#!/usr/bin/env python3
from src.utils.config import Config
from src.utils.exporter import Exporter
from src.variator import Variator
import sys
import os
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from src.simulations.simulation_controller import SimulationController
from src.utils.util_functions import setup_paths
from multiprocessing import cpu_count

#======================
#start of user config section
#======================
user_config={
    "config_name":"config_example_singleFamilyHouse.json",
    "output_path":"output",
    "fmu_name_windows":"Model_0v1_0interiorWalls_0Floor_0Roof_0Pctrl_win64.fmu",
    "fmu_name_linux":"Model_0v1_0interiorWalls_0Floor_0Roof_0Pctrl_linux.fmu"
}
#======================
#end of user config section
#======================


def worker_start(worker_id: int, config: Config, variation: Variator):
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
                    variation=variation)
    
    rows, header, converted_variation = worker.simulate_fmu()
    worker.fmu_wrapper.terminate_fmu()
    return rows, header, converted_variation, variation

if __name__ == "__main__":
    time_begin=time.time()
    config_path, fmu_path, output_path = setup_paths(user_config)

    print("\n")
    print(f"used FMU-File:\t\t'{fmu_path}' (last modified: {time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(os.path.getmtime(fmu_path)))})")
    print(f"used config-File:\t'{config_path}'")
    print(f"used output directory:\t'{output_path}'")
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
        futures = [executor.submit(worker_start, i+1, config, variation) for i, variation in enumerate(variation_list)]

        total_tasks = len(futures)
        completed_tasks = 0
        print(f"Total tasks: {total_tasks}. Computing...\n")
        
        # Loop through the completed futures as they finish
        for future in as_completed(futures):
            completed_tasks += 1
            
            rows, header, converted_variation, original_variation = future.result()
            
            exporter.export_csv(rows=rows, 
                                header=header, 
                                info=converted_variation, 
                                param_input_list=original_variation, 
                                var_param=variated_config_parameters)

            sys.stdout.write(f"\rTasks completed: {completed_tasks}/{total_tasks}, total runtime: {round(time.time()-time_begin,2)} s\n")
            sys.stdout.flush()
        
        print(f"\nAll tasks are done!\n\n")
        
    #print("-----------evaulation-----------")
    #import plausibility_check_test
    #import validation_ashrae_test_cases
    #import test_compare_two_runs


