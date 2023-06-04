#from datetime import date
#from urllib.parse import unquote

TYPE_Bool = "java.lang.Boolean"
TYPE_Map = "java.util.Map"
TYPE_String = "java.lang.String"
TYPE_Date = "com.bodet.bwt.core.type.time.BDate"
TYPE_Int = "java.lang.Integer"
TYPE_Short = "java.lang.Short"
TYPE_Long = "java.lang.Long"
TYPE_List = "java.util.List"
TYPE_BWPResponse = "com.bodet.bwt.core.type.communication.BWPResponse"
TYPE_CalendrierDemandesDataBWT = "com.bodet.bwt.gtp.serveur.domain.commun.intranet_calendrier_absence.CalendrierDemandesDataBWT"
TYPE_CalendrierDemandeJourDataBWT = "com.bodet.bwt.gtp.serveur.domain.commun.intranet_calendrier_absence.CalendrierDemandeJourDataBWT"
TYPE_CalendrierAbsenceCellBWT = "com.bodet.bwt.gtp.serveur.domain.commun.intranet_calendrier_absence.CalendrierAbsenceCellBWT"
TYPE_CalendrierTeletravailCellBWT = "com.bodet.bwt.gtp.serveur.domain.commun.intranet_calendrier_absence.CalendrierTeletravailCellBWT"
TYPE_BColor = "com.bodet.bwt.core.type.drawing.BColor"
TYPE_BTrame = "com.bodet.bwt.core.type.drawing.BTrame"
TYPE_Enum = "ENUM"


class BodetCalDay():
	ferie = False
	absent = False
	teletravail = False
	
	def __init__(self, data):
		i = 0
		while i < len(data):
			if data[i] == 'abs':
				self.absent = True
				i += 1
			elif data[i] == 'tt':
				self.teletravail = True
				i += 1
			elif type(data[i]) == dict and 'bcolor' in data[i]:
				i += 5
			elif type(data[i]) == dict and 'str' in data[i]:
				if self.teletravail: 
					self.teletravail = data[i]['str']
				elif self.absent:
					self.absent = data[i]['str']
				i += 1
			elif type(data[i]) == bool:
				self.ferie = data[i]
				i += 3
			else:
				i += 1

	def __str__(self):
		return "férié: %s absence: %s télétravail: %s" % (self.ferie, self.absent, self.teletravail)


class BodetCalendar():
	def __init__(self, data):
		data_list = data.split(',')
		print("number of items : ", len(data_list))
		
		num = int(data_list[0])
		types = data_list[1:num+1]
		types = [ s.strip('"') for s in types ]
		values = data_list[num+1:]
		
		#print("types = ")
		#for i in range(len(types)):
		#	print(i, types[i])
		#print("values = ", values)
		
		self.calendar = self.__decode_data(types, values)
		#print(self.calendar)
		
		# convert items
		for date in self.calendar:
			self.calendar[date] = BodetCalDay(self.calendar[date])
		

	# days : return a list of datetime dates from calendar
	def days(self):
		return [ date_str for date_str in sorted(self.calendar)]

	# get_day: return BodetCalDay object for given day (YYYYMMDD format)
	def get_day(self, day):
		return self.calendar[day]
		
	##### PRIVATE FUNCTIONS ####
	def __decode_data(self, types, values):
		cal = {}
		date = None
		nb_dates = int(values[6]) + 1
		#print("nb_dates = ", nb_dates)
		#print("nb_types = ", len(types))
		i = 7
		while i < len(values) and nb_dates > 0:
			t = int(values[i])
			#print(i, t)
			t_str = types[t] if t in range(len(types)) else None
			#if t_str: print(t_str)

			if t_str == TYPE_Map:
				date = None
				i += 1

			elif t_str == TYPE_Date:
				date = str(values[i+1])
				nb_dates -= 1
				i += 1
			
			elif t_str == TYPE_CalendrierDemandeJourDataBWT:
				cal[date] = tuple()
			
			elif t_str == TYPE_CalendrierAbsenceCellBWT:
				if date in cal:
					cal[date] += ('abs',)
			
			elif t_str == TYPE_CalendrierTeletravailCellBWT:
				if date in cal:
					cal[date] += ('tt',)
			
			elif t_str == TYPE_BColor:
				if date in cal:
					cal[date] += ({'bcolor': int(values[i+1])},)
				i += 1
			
			elif t_str == TYPE_BTrame:
				if date in cal:
					cal[date] += ({'btrame': bool(int(values[i+1]))},)
				i += 1
				
			elif t_str == TYPE_String:
				index = int(values[i+1])
				string = str(types[index]) if index < len(types) else '?'
				if date in cal:
					#cal[date] += ({'str': unquote(string)},)
					cal[date] += ({'str': string},)
				i += 1
				
			elif t_str in [ TYPE_Int, TYPE_Short, TYPE_Long ]:
				if date in cal:
					cal[date] += (int(values[i+1]),)
				i += 1
				
			elif t_str == TYPE_Bool:
				if date in cal:
					cal[date] += (bool(int(values[i+1])),)
				i += 1

			i += 1

		return cal

if __name__ == '__main__':
	file = open("cal_2021.txt", "r")
	cal = BodetCalendar(file.read())
	days = cal.days()
	
	for date in days: 
		print(date, cal.get_day(date))
	
	file.close()
