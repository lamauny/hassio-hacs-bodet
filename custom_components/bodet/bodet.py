from requests import Session
from bs4 import BeautifulSoup
import re
import sys, time
from datetime import date
from bodet_calendar import BodetCalDay, BodetCalendar

##### LOCAL FUNCTIONS ####

def pretty_print_POST(req):
    """
    At this point it is completely built and ready
    to be fired; it is "prepared".

    However pay attention at the formatting used in 
    this function because it is programmed to be pretty 
    printed and may differ from the actual request.
    """
    print('{}\n{}\r\n{}\r\n\r\n{}'.format(
        '-----------START-----------',
        req.method + ' ' + req.url,
        '\r\n'.join('{}: {}'.format(k, v) for k, v in req.headers.items()),
        req.body,
    ))

def pretty_print_resp(resp):
    print('{}\n{}\r\n{}\r\n\r\n{}\r\n{}'.format(
        '-----------RESPONSE-----------',
        str(resp.status_code) + ' ' + resp.reason + ' ' + resp.url,
        '\r\n'.join('{}: {}'.format(k, v) for k, v in resp.headers.items()),
        'Length: %d/%d' % (len(resp.content), len(resp.text)),
        resp.text,
    ))

##### CALENDAR PARSING ####

# Find the index of the given name
def cal_get_index(soup, name):
	table_names = soup.find("table", {"class": "tableAbsenceBordered"})
	#print(table_names)
	index = 0
	for elem in table_names.find_all("div"):
		if elem.has_attr("title") and elem["title"] == name:
			return index;
		index +=1;
	return -1

# Return dictionary of the given day
def cal_get_day_value(day):
	CAL_BG_ABSENT = "#1ab6db"
	value = {"type": "Normal", "state": "Default"}
	if day is None:
		return value
	if day.has_attr("class"):
		value["type"] = day["class"][0]
	for div in day.find_all("div"):
		if div.has_attr("style"):
			if div["style"].startswith("background:"):
				bg_color=div["style"][11:18]
				#print("bg=", bg_color)
				if bg_color == CAL_BG_ABSENT:
					value["state"] = "Absent"
			if div["style"].startswith("background-image:"):
				value["state"] = "HomeWork"
	return value

# Get today soup for ident at index
def cal_get_today(soup, index):
	table_users = soup.find_all("table", {"class": "tableAbsenceBordered"})[1]
	#print(table_users)
	table_index = table_users.find_all("tr", {"class": "lignePlanningGroupe"})[index];
	#print(table_index)
	table_days = table_index.find_all("td");
	#print(table_days)
	for day in table_days:
		#print(get_day_value(day))
		if day.has_attr("class"): 
			#print(day["class"])
			if "calendrierMoisToday" in day["class"]:
				today = day
	#print(today)
	return today

# Encode payload (reverse engineering from java code)
def encode_payload(t, p):
	enc = bytes()
	payload = str.encode(p)
	for c in range(len(payload)):
		enc += bytes({payload[c] + t[c % len(t)] - c % 17 & 0xff})
	return enc

##### BODET CLASS ####

class Bodet(Session):
	URL_MAIN = 'https://smgroup.bodet-software.com'
	URL_LOGIN = 'https://smgroup.bodet-software.com/open/login'
	URL_LOGIN_POST = 'https://smgroup.bodet-software.com/open/j_spring_security_check'
	URL_ACTION = 'https://smgroup.bodet-software.com/open/da'
	URL_BADGE = 'https://smgroup.bodet-software.com/open/webgtp/badge'
	URL_INTRANET = 'https://smgroup.bodet-software.com/open/homepage?ACTION=intranet&asked=1&header=0'
	URL_CALENDAR = 'https://smgroup.bodet-software.com/open/bwt/intranet_calendrier_absence.jsp'
	URL_CAL_DATA = 'https://smgroup.bodet-software.com/open/bwpDispatchServlet?'

	USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36'
	
	def __init__(self, username, password):
		Session.__init__(self)
		
		self.username = username
		self.password = password
		headers = {
			'DNT': '1',
			'Content-Type': 'application/x-www-form-urlencoded',
			'Origin': self.URL_MAIN,
			'Referer': self.URL_LOGIN, 
			'User-Agent': self.USER_AGENT
		}
		# Open the login page
		#session.headers.update(headers)
		server = self.get(self.URL_LOGIN)

		# Update the headers
		server.headers.update(headers)
		#print("headers:", server.headers)

		# Retreive the CSRF token
		self.csrf = re.search('name="_csrf_bodet" value="([a-z,0-9,-]*)', server.text)[1]
		
		login_data = {
			'ACTION': 'ACTION_VALIDER_LOGIN',
			'username': self.username,
			'password': self.password,
			'_csrf_bodet': self.csrf
			}
		#print("post data:", login_data)

		# Login
		server = self.post(self.URL_LOGIN_POST, data=login_data, headers=headers)
		#print('LOGIN REQ: \n')
		#pretty_print_POST(server.request)
		#print('LOGIN RESP: \n', server.text) 
		if re.search('ACTION_VALIDER_LOGIN', server.text):
			raise Exception("Login failed")
	
		# Retreive the JETON_INTRANET
		server = self.get(self.URL_INTRANET)
		#print('INTRANET RESP: \n', server.text) 
		self.jeton = re.search('name="JETON_INTRANET" id="JETON_INTRANET" value="([0-9]*)', server.text)[1]
		#print('JETON_INTRANET=', self.jeton)
		self.fullname = re.search('<td class="titre" id="badgeur">(.*)</td>', server.text)[1]
		#print('FULL NAME=', self.fullname)



	# Badger entree/sortie
	def badger_es(self):
		headers = {
			'DNT': '1',
			'Content-Type': 'application/x-www-form-urlencoded',
			'initiator': self.URL_MAIN,
			'Origin': self.URL_MAIN,
			'Referer': self.URL_ACTION, 
			'User-Agent': self.USER_AGENT
		}
		action_data = {
			'ACTION': 'BADGER_ES',
			'ACTION_SWITCH': '',
			'JETON_INTRANET': jeton,
			'choixApplication': '',
			'_csrf_bodet': csrf
		}
		server = self.post(self.URL_ACTION, data=action_data, headers=headers)
		#print('REQ: \n')
		#pretty_print_POST(server.request)
		#print('RESP: \n', server.text)
		return server.text

	# Suis-je absent aujourd'hui ?
	def get_abs_today(self):
		soup = self.__cal_get_abs()

		my_index = cal_get_index(soup, self.fullname)
		#print("my_index=", my_index)
		if my_index == -1:
			raise Exception("Unable to find calendar for %s" % self.fullname)
		today = cal_get_today(soup, my_index)
		#print("today=", today)
		value = cal_get_day_value(today)
		#print("value=", value)
		return value

	# Connect calendar
	def calendar_connect(self):
		#print("\n--- calendar connect ---")
		PAYLOAD='9,"com.bodet.bwt.core.type.communication.BWPRequest","java.util.List","java.lang.Short","java.lang.Long","NULL","java.lang.String","' + self.csrf + '","connect","com.bodet.bwt.server.mouse.service.GlobalBWTService",0,1,2,2,16,3,392,549368286,4,5,6,5,7,5,8'
		#print("payload = ", PAYLOAD)
		headers = {
			'DNT': '1',
			'Accept-Encoding': 'gzip, deflate, br',
			'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
			'Content-Type': 'text/bwp;charset=UTF-8',
			'Host': 'smgroup.bodet-software.com',
		#	'X-KELIO-STAT': 'cst=' + str(int(time.time())),
		#	'If-Modified-Since': 'Thu, 01 Jan 1970 00:00:00 GMT',
		#	'initiator': URL_MAIN,
			'Origin': self.URL_MAIN,
			'Referer': self.URL_CALENDAR, 
			'User-Agent': self.USER_AGENT
		}
		server = self.post(self.URL_CAL_DATA + str(int(time.time())), data=PAYLOAD, headers=headers)
		#pretty_print_POST(server.request)
		#pretty_print_resp(server)
		self.cal_myst_number = server.text.split(',')[-6]

	# Get calendar
	def calendar_get(self, year):
		#print("\n--- get_calendar ---")
		PAYLOAD='11,"com.bodet.bwt.core.type.communication.BWPRequest","java.util.List","java.lang.Integer","com.bodet.bwt.core.type.time.BDate","com.bodet.bwt.gtp.serveur.domain.commun.intranet_calendrier_absence.CalendrierAbsenceConfigurationBWT","java.lang.Boolean","NULL","java.lang.String","' + self.csrf + '","getAbsencesEtJoursFeries","com.bodet.bwt.gtp.serveur.service.intranet.calendrier_absence.CalendrierAbsenceSalarieBWTService",0,1,5,2,302,3,'+ str(year) + '0101,3,' + str(year) + '1231,4,5,1,5,0,5,1,5,1,5,1,5,1,6,6,5,1,6,6,2,3,2,' + self.cal_myst_number + ',7,8,7,9,7,10'
		#print("payload = ", PAYLOAD)
		ENTETE=str.encode('¤=0123456789:01')
		TABLE=[0] * 13
		headers = {
			'DNT': '1',
			'Accept-Encoding': 'gzip, deflate, br',
			'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
			'Content-Type': 'text/bwp;charset=UTF-8',
			'Host': 'smgroup.bodet-software.com',
			'Origin': self.URL_MAIN,
			'Referer': self.URL_CALENDAR, 
			'User-Agent': self.USER_AGENT
		}
		calendar_data = ENTETE + encode_payload(TABLE, PAYLOAD)
		server = self.post(self.URL_CAL_DATA + str(int(time.time())), data=calendar_data, headers=headers)
		#print('ABS REQ: \n')
		#pretty_print_POST(server.request)
		#pretty_print_resp(server)
		#cal_file = open("resp_cont.txt", "bw")
		#cal_file.write(server.content)
		#cal_file.close()
		#print('CAL RESP: \n', server.iter_content())
		#print('CAL RESP: \n', server.content)
		return BodetCalendar(server.content.decode())

	# Get today from calendar
	def calendar_get_today(self):
		today = date.today()
		cal = self.calendar_get(today.year)
		return cal.get_day(today.strftime("%Y%m%d"))

	##### PRIVATE FUNCTIONS ####

	# Get calendar
	def __cal_get_abs(self):
		headers = {
			'DNT': '1',
			'Content-Type': 'application/x-www-form-urlencoded',
			'parentDocumentId': '0C31E89FFE84097948DE178D91926E3C',
			'documentLifecycle': 'active',
			'frameType': 'sub_frame',
			'Upgrade-Insecure-Requests': '1',
			'initiator': self.URL_MAIN,
			'Origin': self.URL_MAIN,
			'Referer': self.URL_ACTION, 
			'User-Agent': self.USER_AGENT
		}
		calendar_data = {
			'ACTION': 'AFFICHER_CALENDRIER_ABSENCES_SERVICE_',
			'ACTION_SWITCH': '',
			'JETON_INTRANET': self.jeton,
			#'annee': '2023',
			'application': '6',
			'choixApplication': '',
			'choixOption': '',
			'eltPeriodeVisualisee': '0,2',
			'listeEtatsDemandesInfos': '',
			#'modeAnnee': 'true',
			#'mois': '4',
			'_csrf_bodet': self.csrf
		}
		server = self.post(self.URL_ACTION, data=calendar_data, headers=headers)
		#print('ABS REQ: \n')
		#pretty_print_POST(server.request)
		#print('ABS RESP: \n', server.text)
		#cal_file = open("calendar.htm", "w")
		#cal_file.write(server.text)
		#cal_file.close()
		return BeautifulSoup(server.text,features="lxml")

if __name__ == '__main__':

	bodet = Bodet('user', 'pwd')

	#bodet.badger_es()

	print(bodet.get_abs_today())
	
	bodet.calendar_connect()
	print(bodet.calendar_get_today())
