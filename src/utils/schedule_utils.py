from src.utils.util_functions import parse_duration, get_step_size_arr

def parse_schedule(schedule: dict, global_start: int, global_stop: int):
	'''
	parses the schedule dict (of type {<timestamp>: {<event/parameter>: <value>}}):
		- converts time strings to int
		- converts occupancy short notation to full filepaths
		- joins double entries (if one was entered in string format and one in seconds)
		- filters out events that lie outside of simulation range
		- sorts all entries

	arguments:
		schedule: dictionary of retrofit and occupancy change schedule, passed right down from json through main
		global_start: start_time as defined in main simulation config
		global_stop: stop_time as defined in main configuration config

	returns:
		schedule: formatted schedule dict
	'''
	# convert timestamps to seconds in int and filter for events outside start_time, stop_time
	parsed_times = [(parse_duration(time) if isinstance(time, str) else time, schedule[time]) for time in schedule]
	parsed_times = [(timestamp, event) for timestamp, event in parsed_times if global_start < timestamp < global_stop]


	joined_events = {}
	for timestamp, entry in parsed_times:
		# convert Occupancy short notation to builda parameter
		if "Occupancy" in entry:
			entry["internalGain.fileName"] = get_intGainProfile_from_shortname(entry["Occupancy"])
			entry["hygienicalWindowOpening.fileName"] = get_winOpProfile_from_shortname(entry["Occupancy"])
			entry.pop("Occupancy")

		# combine events should one have been specified as string and one as int
		already_there = False
		for key in joined_events:
			if key == timestamp:

				joined_events[key].update(entry)

				already_there = True
		if not already_there:
			joined_events[timestamp] = entry


	sorted_events = dict([(timestamp, joined_events[timestamp]) for timestamp in sorted(joined_events)])

	return sorted_events



	


def schedule_step_size_array(start_time: int,
								stop_time: int,
								writer_step_size: int,
								controller_step_size: int,
								max_permitted_time_step: int,
								schedule: dict):

	'''
	executes src.utils.util_functions.get_step_size_array for a schedule containing halting points
	arguments:
		- start_time, stop_time, writer_step_size, controller_step_size, max_permitted_time_step: directly passed to get_step_size_arr()
		- schedule: dictionary {<starttime in s (int)>: {<parameter_name>:<new_value>}}
	returns:
		- step_size_arrays: list of returns of get_step_size_arr() from retrofit to next retrofit respectively
		- timestamps[:-1]: list of halting points (correlated to step_size_arrays) for retrofits

	'''

	timestamps = [start_time] + list(schedule) + [stop_time]

	step_size_arrays = []
	for start, stop in zip(timestamps[:-1], timestamps[1:]):

		step_size_arrays.append(get_step_size_arr(start,
													stop,
													writer_step_size,
													controller_step_size,
													max_permitted_time_step))
	return step_size_arrays, timestamps[:-1]


def get_intGainProfile_from_shortname(shortname):
	'''
	maps short internalGain Profile names to their full file path
	arguments:
		- shortname: Pre-specified short name for one internalGain Profile
	returns:
		- full filepath if the internalGain Profile exists
	'''
	base_path = "resources/internalGainProfiles/"
	match shortname:
		case "Empty":
			return base_path + "NoActivity.txt"
		case "base_example":
			return base_path + "internalGains.txt"
		case "ASHRAE_BASE_EXAMPLE":
			return base_path + "ASHRAE_TEST_CASE_PROFILE.TXT"
		case "Couple_both_at_work":
			return base_path + "CHR01_Couple_both_at_Work_power_with_human_heat.txt"
		case "Single_with_work":
			return base_path + "CHR07_Single_with_work_power_with_human_heat.txt"
		case "Couple_over_65":
			return base_path + "CHR16_Couple_over_65_years_power_with_human_heat.txt"
		case "Family_both_at_work_2_children":
			return base_path + "CHR27_Family_both_at_work_2_children_power_with_human_heat.txt"
		case "Student_Flatsharing":
			return base_path + "CHR52_Student_Flatsharing_power_with_human_heat.txt"
		case _:
			raise LookupError(f"shortname {shortname} for internalGainProfile not specified. Look into src/utils/schedule_utils for further information.")


def get_winOpProfile_from_shortname(shortname):
	'''
	maps short windowOpening Profile names to their full file path
	arguments:
		- shortname: Pre-specified short name for one windowOpening Profile
	returns:
		- full filepath if the windowOpening Profile exists
	'''
	base_path = "resources/hygienicalWindowOpeningProfiles/"
	match shortname:
		case "Empty":
			return base_path + "no_opening.txt"
		case "base_example":
			return base_path + "conscient.txt"
		case "ASHRAE_BASE_EXAMPLE":
			return base_path + "no_opening.txt"
		case "Couple_both_at_work":
			return base_path + "CHR01_Couple_both_at_Work_window_opening.txt"
		case "Single_with_work":
			return base_path + "CHR07_Single_with_work_window_opening.txt"
		case "Couple_over_65":
			return base_path + "CHR16_Couple_over_65_years_window_opening.txt"
		case "Family_both_at_work_2_children":
			return base_path + "CHR27_Family_both_at_work_2_children_window_opening.txt"
		case "Student_Flatsharing":
			return base_path + "CHR52_Student_Flatsharing_window_opening.txt"
		case _:
			raise LookupError(f"shortname {shortname} for windowOpeningProfile not specified. Look into src/utils/schedule_utils for further information.")




def get_index_from_dict_like_array(arr, key):
	'''
	returns index for key-specified entry in dict-like array (list(dict.items()))
	arguments:
		- arr: dict-like array
		- key: key to the entry
	returns:
		- index of entry, -1 if entry does not exist
	'''
	for index, (k,v) in enumerate(arr):
		if k == key:
			return index
	return -1


def check_for_invalid_keys(schedule: dict, config: dict):
	'''
	Checks if all parameters used in the schedule are contained in the general config.
	Raises a KeyError if not.
	arguments:
		- schedule: {timestamp: {parameter, new_value}}. All parameters are compared against config
		- config: variation part of the global BuilDa config {key: value}
	raises:
		- KeyError if a parameter of the schedule cannot be found as key in config.
	'''
	updated_parameters = []
	# iterate over all timestamps over all parameters of the schedule
	for event in schedule.values():
		for key in event.keys():
			updated_parameters.append(key)
	# remove all keys that also exist as config keys
	residual_keys = set(updated_parameters)-set(config.keys())
	residual_keys.discard("Heater")
	# if any keys are left, raise KeyError
	if len(residual_keys) != 0:
		raise KeyError(f"Scheduled parameter(s) {residual_keys} do not exist. Please check your schedule.json")


