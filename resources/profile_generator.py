import numpy as np
import calendar
import re
import pandas as pd


remove_feb29th = True	#shorten gap years

mean_person_weight = 70 #[kg], no permutation implemented yet

rmr = 1.1622222222 * mean_person_weight # as in https://pubmed.ncbi.nlm.nih.gov/8292105/
persons_in_met_profile = 2 #how many persons are described by the int_gain_met_profile table

int_gain_met_profile = [ #[MET = WMR/RMR] ratio to resting metabolic rate; (hour of day, [holiday, workday, saturday, sunday])
	[2,	2,	2,	2],
	[2,	2,	2,	2],
	[2,	2,	2,	2],
	[2,	2,	2,	2],
	[2,	2,	2,	2],
	[2,	2,	2,	2],
	[2,	2,	2,	2],
	[2,	1,	2,	2],
	[2,	0,	2,	2],
	[0,	0,	2,	0],
	[0,	0,	2,	0],
	[0,	0,	2,	0],
	[0,	0,	5,	0],
	[0,	0,	5,	0],
	[0,	0,	5,	0],
	[0,	0,	5,	0],
	[0,	1,	5,	0],
	[0,	1,	5,	0],
	[0,	3,	5,	0],
	[0,	3,	5,	0],
	[2,	3,	2,	0],
	[2,	2,	2,	2],
	[2,	2,	2,	2],
	[2,	2,	2,	2]]

int_gain_non_human_profile = [ #[W]; (hour of day, [holiday, workday, saturday, sunday])
	[0,	0,	0,	0],
	[0,	0,	0,	0],
	[0,	0,	0,	0],
	[0,	0,	0,	0],
	[0,	0,	0,	0],
	[0,	0,	0,	0],
	[0,	0,	0,	0],
	[0,	0,	0,	0],
	[0,	0,	0,	0],
	[0,	0,	0,	0],
	[0,	0,	0,	0],
	[0,	0,	0,	0],
	[0,	0,	0,	0],
	[0,	0,	0,	0],
	[0,	0,	0,	0],
	[0,	0,	0,	0],
	[0,	0,	0,	0],
	[0, 0,	0,	0],
	[0,	0,	0,	0],
	[0,	0,	0,	0],
	[0,	0,	0,	0],
	[0,	0,	0,	0],
	[0, 0,	0,	0],
	[0,	0,	0,	0]]


def get_calendar_year(year):
	'''
	generate a list of days from Jan 1st to Dec 31st of the specified year
	args:
		- year: the year the types of day are taken from
	returns:
		- dates: list of days
	'''

	#create a year specific calendar object
	cal = calendar.Calendar()

	#generate a list of valid dates that lie in the year, with weekdays
	val = np.concatenate([list(cal.itermonthdays(year, m)) for m in range(1,13)])
	dates = np.concatenate([np.array(list(cal.itermonthdays4(year, m))) for m in range(1,13)])
	boolarr = []
	for i in val:
		if i > 0:
			boolarr.append(True)
		else:
			boolarr.append(False)
	dates = dates[boolarr]
	if remove_feb29th:
		for date in dates:
			if all(date[1:3] == [2, 29]):
				dates = np.concatenate([dates[:59], dates[60:]])
				break
	return dates

def generate_calendar(year):
	'''
	arguments:
		- year: the year a calendar is to be generated for
	returns:
		- dates: list of days from Jan 1st to Dec. 31st containing information about daytype (workday, holiday, ...)
	'''

	#statically define holidays
	holidays = [[2025, 1, 1], [2025, 1, 6], [2025, 4, 17],[2025, 4, 18], [2025, 4, 20], [2025, 4, 21], [2025, 5, 1], [2025, 5, 29], [2025, 6, 8], [2025, 6, 9], [2025, 6, 19], [2025, 8, 15], [2025, 10, 3], [2025, 10, 31], [2025, 11, 1], [2025, 11, 19], [2025, 12, 25], [2025, 12, 26]]
	
	#generate list of dates with a boolean (day[4]) if the day is a holdiay or not
	dates = get_calendar_year(year)
	dates = np.concatenate((dates, np.zeros((dates.shape[0], 1), dtype = np.int8)), axis = 1)
	for day in dates:
		for h in holidays:
			if all(day[1:3] == h[1:3]) or all(day[0:3] == h):
				day[4] = 1
	return dates



def generate_internalGainProfile_spec_time(time, 					#eg [[2025, 01, 01], [2025, 01, 31]]
									rmr = rmr,
									met_profile = int_gain_met_profile,
									mech_profile = int_gain_non_human_profile,
									n_persons = 1,
									sleeptime = [22, 6]):
	'''
	generates a internalGainProfile by multiplying the specified met profile by the rmr for each day type
	arguments:
		- time: date range to generate a profile for in format [[year, month, day], [year, month, day]]
		- rmr: average resting metabolic rate to be used (Power in [W] an average person emits while resting)
		- met_profile: profile of shape [hour, daytype] of MET (metabolic task equivalent) values (rmr*MET = actual emitted power)
		- mech_profile: absolute mechanical and/or electrical emissions in Watts
		- n_persons: how many persons contribute to the emissions
		- sleeptime: [hh, hh] time period in which occupants sleep -> met = 1 (can be [1, 7] or [17, 23])
	returns:
		- table containing intGainProfile containing two columns: time [h] and gains [W]
	'''

	#convert arrays
	met_profile = np.array(met_profile)
	mech_profile = np.array(mech_profile)
	n_years = int(time[1][0]) - int(time[0][0]) + 1

	#make sure met os constant while sleeping
	for hour in range(met_profile.shape[0]):
		for entry in range(met_profile.shape[1]):
			if not check_sleep_time(hour, sleeptime):
				met_profile[hour, entry] = persons_in_met_profile  #every person emits RMR while sleeping https://doi.org/10.1038/sj.ijo.0801922


	#generate calendar with holidays and take subset defined via time
	dates = np.concatenate([generate_calendar(y+int(time[0][0])) for y in range(n_years)])
	start_index = 0
	stop_index = 0
	for i, day in enumerate(dates):
		if (all(day[0:3] == time[0])):
			start_index = i
		elif(all(day[0:3] == time[1])):
			stop_index = i
	dates = dates[start_index:stop_index+1]

	#calculate int gains using provided profiles and day info
	out = []
	for day in dates:
		if day[4] == 1:	#holiday
			out.append(met_profile.T[0]*rmr*n_persons/persons_in_met_profile+mech_profile.T[0])
		elif day[3] == 6:	#sunday
			out.append(met_profile.T[3]*rmr*n_persons/persons_in_met_profile+mech_profile.T[3])
		elif day[3] == 5:	#saturday
			out.append(met_profile.T[2]*rmr*n_persons/persons_in_met_profile+mech_profile.T[2])
		else:				#workday
			out.append(met_profile.T[1]*rmr*n_persons/persons_in_met_profile+mech_profile.T[1])

	out = np.concatenate(np.array(out))
	# time unit: min
	return np.array([np.linspace(0, out.shape[0]-1, out.shape[0], dtype = np.int64)*60, out]).T


def generate_windowOpeningProfile_spec_time(time, 					#eg [[2025, 01, 01], [2025, 01, 31]]
									sleeptime = [22, 6],
									met_profile = int_gain_met_profile,
									n_persons = 2,
									conscientiousness = 1,
									open_after_minutes = 120,
									offset = 0):
	'''
	generates a windowOpeningProfile over time by employing daytypes and eval_wOpening()
	arguments:
		- time: date range to generate a profile for in format [[year, month, day], [year, month, day]]
		- met_profile: profile of shape [hour, daytype] of MET (metabolic task equivalent) values (rmr*MET = actual emitted power)
		- conscientiousness: parameter describing how sensitive occupants react to "bad air"
		- n_persons: how many persons contribute to the emissions
		- sleeptime: [hh, hh] time period in which occupants sleep -> won't open windows (can be [1, 7] or [17, 23])
		- open_after_minutes: parameter after what time (emitting rmr) the air-qualitiy is bad enough to open window
	returns:
		- table containing windowOpeningProfile containing two columns: time [min] and if window is open [bool]
	'''
	
	met_profile = np.array(met_profile)
	n_years = int(time[1][0]) - int(time[0][0]) + 1

	#generate calendar with holidays and take subset defined via time
	dates = np.concatenate([generate_calendar(y+int(time[0][0])) for y in range(n_years)])
	start_index = 0
	stop_index = 0
	for i, day in enumerate(dates):
		if (all(day[0:3] == time[0])):
			start_index = i
		elif(all(day[0:3] == time[1])):
			stop_index = i
	dates = dates[start_index:stop_index+1]

	#evolve windowOpeningScore (out[*, 1]) over time using personminutes spent in the house (out[*, 0]) and store if window was opened (out[*, 2])
	out = [[0, 0, 0]]
	for day in dates: 							#every day
		for i in range (met_profile.shape[0]):	#every hour
			for k in range(12):					#every 5mins
				if day[4] == 1:	#holiday
					out.append(eval_wOpening(out[-1][0], i, met_profile.T[0,i], sleeptime, conscientiousness, out[-1][2], n_persons, open_after_minutes))
				elif day[3] == 6:	#sunday
					out.append(eval_wOpening(out[-1][0], i, met_profile.T[3,i], sleeptime, conscientiousness, out[-1][2], n_persons, open_after_minutes))
				elif day[3] == 5:	#saturday
					out.append(eval_wOpening(out[-1][0], i, met_profile.T[2,i], sleeptime, conscientiousness, out[-1][2], n_persons, open_after_minutes))
				else:				#workday
					out.append(eval_wOpening(out[-1][0], i, met_profile.T[1,i], sleeptime, conscientiousness, out[-1][2], n_persons, open_after_minutes))

	#append linear timestamps in 5min-intervals to the window open boolean
	return np.array([np.linspace(0, len(out)-2, len(out)-1)*5, np.array(out[1:]).T[2]], dtype = int).T

def eval_wOpening(lastvalue, hour, met, sleeptime, conscientiousness, winOpen, n_persons, open_after_minutes):
	"""
	Calculates the windowOpeningScore (wOpScore) used the formula from the profileGenerator_occupation_window_gains.ods excel file
	I simplified it a bit since the floor area did not seem to be used in the excel file:
	wOpScore = (sleeping!=0)*(#persons>0)*time_since_last_opening*(met/n_persons + 1 {rel. floor area in the excel file, not necessary imo})*conscientiousness with dtslo/dt = dt
	"""
	if winOpen:
		return [0,0,0]
	#wOpScore = int(check_sleep_time(hour, sleeptime))*int(met>0)*(lastvalue+5*met)*conscientiousness
	wOpScore = int(check_sleep_time(hour, sleeptime))*int(met>0)*(met/n_persons + 1)*conscientiousness*(lastvalue+5)
	if wOpScore >= open_after_minutes:	
		return [lastvalue+5, wOpScore, 1]
	else:
		return [lastvalue+5, wOpScore, 0]


def check_sleep_time(hour, sleeptime):
	#checks if the provided hour outside the time interval [from, to] provided via sleeptime. Used for wOpeningScore and matching met values to sleeping cycle
	if (sleeptime[0] > sleeptime[1]):
		return hour<sleeptime[0] and hour >= sleeptime[1]
	elif(sleeptime[0] < sleeptime[1]):	#person does not sleep through the classical night
		return hour<sleeptime[0] or hour >= sleeptime[1]
	else:
		return False



def generate_profiles(gain_filename, win_filename, gain_subfolder = "internalGainProfiles", win_subfolder = "hygienicalWindowOpeningProfiles"):
	'''
	wrapper for the whole generation process.
	arguments:
		- gain_filename: filename to give the internalGainProfile file
		- win_filename: filename to give the windowOpeningProfile file
		- gain_subfolder: in which subfolder to store the internalGain file
		- win_subfolder: in which subfolder to store the windowOpening file
	returns:
		- paths to the respective profiles

	''' 
	intGainProfile =  generate_internalGainProfile_spec_time([[2025, 1, 1], [2025, 12, 31]],
									rmr = rmr,
									met_profile = int_gain_met_profile,
									mech_profile = int_gain_non_human_profile,
									n_persons = 2,
									sleeptime = [22, 6]) 
	winOpProfile = generate_windowOpeningProfile_spec_time([[2025, 1, 1], [2025, 12, 31]],
									sleeptime = [22, 6],
									met_profile = int_gain_met_profile,
									n_persons = 2,
									conscientiousness = 1,
									open_after_minutes = 120)

	#fix improper filenaming
	if not gain_filename.endswith(".txt"):
		gain_filename = gain_filename + ".txt"
	if not win_filename.endswith(".txt"):
		win_filename = win_filename + ".txt"	

	#store the .txt files
	with open(gain_subfolder + "/" + gain_filename, "w", newline = "") as f:
		f.write(f"#1 minutes\tinternal_gains_zone1\ndouble heatGain{intGainProfile.shape}\n")
		pd.DataFrame(intGainProfile).to_csv(f, sep = "\t", header = False, index = False)
	print(f">>>>internalGainProfile saved under {gain_subfolder}/{gain_filename}")
	with open(win_subfolder + "/" + win_filename, "w", newline = "") as f:
		f.write(f"#1 minutes\twindow opened\ndouble hygienicalWindowOpening{winOpProfile.shape}\n")
		pd.DataFrame(winOpProfile).to_csv(f, sep = "\t", header = False, index = False)
	print(f">>>>hygienicalWindowOpeningProfile saved under {win_subfolder}/{win_filename}")

	return gain_subfolder+"/"+gain_filename, win_subfolder+"/"+win_filename



def __main__():
	generate_profiles("generated_intGainProfile.txt", "generated_windowOpeningProfile.txt")

if __name__ == "__main__":
	__main__()	