#!/usr/bin/env python3
from src.utils.config import Config
from src.utils.exporter import Exporter
from src.variator import Variator
import sys
import os
import time,datetime
import zipfile
from concurrent.futures import ProcessPoolExecutor, as_completed
from src.simulations.simulation_controller import SimulationController
from src.utils.util_functions import setup_paths
from multiprocessing import cpu_count

#======================
#start of user config section
#======================
user_config={
    "config_name":"config_example_singleFamilyHouse.json",
    "schedule_name": None,
    "output_path":"output",
    "fmu_name_windows":"Model_v1_interiorWalls_Floor_Roof_Pctrl_windows_openmodelica_v2.fmu",
    "fmu_name_linux":"Model_v1_interiorWalls_Floor_Roof_Pctrl_linux_openmodelica_v2.fmu",
    "multiprocessing":True
}
#======================
#end of user config section
#======================


def worker_start(worker_id: int, config: Config, variation: Variator, schedule = None):
    """
    Entry point for a worker thread that executes a simulation.

    This function initializes a SimulationController for the worker, 
    runs the simulation, and terminates the simulation process afterward.

    Args:
        worker_id (int): The unique identifier for the worker thread.
        config (Config): Settings for the simulation series.
        variation (Variator): Variation of model parameters for the current simulation to use

    Returns:
        tuple: A tuple containing:
            - rows: The results of the simulation.
            - header: The header information of the simulation results.
            - variation: Variation of model parameters used for the current simulation
            - converted_variation: The processed variation of model parameters used in the simulation.
    """
    print(f'Worker {worker_id} starting to work!  ')
    worker = SimulationController(worker_id=worker_id, 
                    config=config,
                    variation=variation,
                    schedule = schedule)
    
    rows, header, converted_variation = worker.simulate_fmu()
    worker.fmu_wrapper.terminate_fmu()
    return rows, header, converted_variation, variation

if __name__ == "__main__":
    time_begin=time.time()
    config_path, fmu_path, output_path, schedule = setup_paths(user_config)
    
    last_modification_timestamp=datetime.datetime(
            *zipfile.ZipFile(fmu_path,"r").getinfo("modelDescription.xml").date_time) \
        .isoformat()
    print("\n")
    print(f"used FMU-File:\t\t'{fmu_path}' \n\t\t\t(last modified: {last_modification_timestamp})")
    print(f"used config-File:\t'{config_path}'")
    print(f"used output directory:\t'{output_path}'")
    print(f"used schedule:\t{schedule}")
    print(f"Multiprocessing:\t'{user_config["multiprocessing"]}'")
    print("\n")

    config = Config(config_path, fmu_path, output_path)

    variator = Variator(config.get('variations'), config.get("variation_type"))

    exporter = Exporter(config.fmu_path, config.config_path, config.output_path)
    exporter.copy_fmu_and_config()
    exporter.save_actual_git_commit_to_dir()

    variation_list = variator.variation_combinations
    variated_config_parameters = variator.get_variated_config_parameters()

    n_workers = cpu_count()
    with ProcessPoolExecutor(max_workers=n_workers) as executor:
        total_tasks = len(variation_list)
        completed_tasks = 0
        print(f"Total tasks: {total_tasks}. Computing...\n")
        
        def export_and_printout(): 
            global completed_tasks 
            completed_tasks+= 1   
            exporter.export_csv(rows=rows, 
                                header=header, 
                                header_time_columns=config.config["time_columns_included"],
                                info=converted_variation, 
                                param_input_list=original_variation, 
                                var_param=variated_config_parameters)
            sys.stdout.write(f"\rTasks completed: {completed_tasks}/{total_tasks}, total runtime: {round(time.time()-time_begin,2)} s\n")
            sys.stdout.flush()

        # Loop through the completed futures as they finish
        if user_config["multiprocessing"]: 
            futures = [executor.submit(worker_start, i+1, config, variation, schedule) for i, variation in enumerate(variation_list)]
            for future in as_completed(futures):
                rows, header, converted_variation, original_variation = future.result()
                export_and_printout()
        else: 
            for variation in variation_list:
                rows, header, converted_variation, original_variation = worker_start(1,config,variation, schedule)
                export_and_printout()
        
        print(f"\nAll tasks are done!\n\n")
        
    #print("-----------evaulation-----------")
    #import plausibility_check_test
    #import validation_ashrae_test_cases
    #import test_compare_two_runs


