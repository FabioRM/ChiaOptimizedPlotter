"""
Fabio Angeletti 2021
fabio.angeletti89@gmail.com

Donations (XCH):  xch164xm4mweuerf8zsf4s2e9nqx4df7ffvfcjcv0dxfva3hhjgg7x6s6sctqr
Donations (ADA):  addr1qxmz3fg5p6hu076yn4z3mv8fdnj7vc4l2q5zqmgsde3zz20yyrrtcmynwfz8lp80nlgxw4tane4grjsajz2a9ddxdmuqnts63g

This python script allows to optimize the amount of parallel plotting processes for CHIA (XCH) mining.

It works as follows:
    1 - clean the temporary folder for plotting (this will destroy any file inside)
    2 - evaluate the amount of free space into the plotting drives (they should be fast SSDs)
    3 - evaluate the amount of free space into the storage drives (for plots storage)
    4 - evaluate CPU and RAM capabilities (number of cores, available RAM)
    5 - generate the correct number of processes and their launch commands
    6 - open a shell for each process and run it
    7 - done

HOW TO USE THE SCRIPT:
    1 - configure the script setting up 5 constants:
        - PLOTTING_DRIVES
        - STORAGE_DRIVES
        - CHIA_LOCATION (it depends also on the version of CHIA you have installed)
        - FARMER_KEY
        - POOL_KEY
    2 - run the script
    3 - check the plotting progress from the shells
    4 - done

IF THE SCRIPT FAILS TO LAUNCH:
    check the console output, keep in mind that possibly you need to install some dependencies (like shutil, psutil)

ADVANCED USERS:
    feel free to customize the script, keep an eye on the PROCESS_INTERVAL_SECONDS. you can use this variable to
    adapt the interval between one process launch and the next. ideally you should set this equal to the time needed
    by you hardware to transfer one plot from a plotting drive to a storage drive. this way your calculator should avoid
    more than one concurrent transfer per drive, reducing mechanical stress and wasted periods of time.
    
    Rule of thumb:
        [DEFAULT] USB 3.0 drives: about 15 minutes (PROCESS_INTERVAL_SECONDS = 900) 
        USB 2.0 drives: about 60 minutes (PROCESS_INTERVAL_SECONDS = 3600)
"""

import sys, os, time, datetime
import multiprocessing, subprocess
import shutil, psutil, glob

# configuration constants. these MUST be configured according to your mining machine, the chia software installed
# and also the ssds and hdds installed
PLOTTING_SLOW_DIRECTORY = "C:/chia/temp_slow"
PLOTTING_FAST_DIRECTORY = "C:/chia/temp_fast"
DESTINATION_TEMPORARY_DIRECTORY = "C:/chia"
STORAGE_DRIVES = [
    "D:/",
    "E:/",
    "F:/",
    "G:/",
    "H:/",
    "I:/",
    "J:/",
    "K:/",
    "L:/",
    "M:/",
    "N:/",
    "O:/",
    "P:/",
    "Q:/",
    "R:/",
    "S:/",
    "T:/",
    "U:/",
    "V:/",
    "W:/",
    "X:/",
    "Y:/",
    "Z:/",
]  # example ["E:/", "F:/", "G:/", "H:/", "I:/"]
MADMAX_CHIA_PLOTTER_LOCATION = "./build/chia_plot"
FARMER_KEY = "a3d6fd875db16e7ccc98ffda929779c1abf9ae852674c5ec7de630defa73852894f131620dafc33874408c8e842ad606"
POOL_KEY = "ae6c61298964c91bbf1ab2b37dece103406ce8012b938f0edddd8ed53074790b839e25008587845317fe24fffbfe3182"

# constants - only advanced users should change them
SLOW_DIR_MIN_AVAILABLE_SPACE = 220
FAST_DIR_MIN_AVAILABLE_SPACE = 110
COMBINED_DIR_MIN_AVAILABLE_SPACE = 256
PLOT_TEMP_SIZE_GIB = 239
PLOT_FINAL_SIZE_GIB = 101.3
RAM_MIB_PER_THREAD = 512
CHECKING_INTERVAL = 300


def print_debug(data=None):
    if data != None:
        print("[%s]\t" % (datetime.datetime.now()) + data)
    else:
        print()


def clean_temporary_folders(
    plotting_slow_directory=PLOTTING_SLOW_DIRECTORY,
    plotting_fast_directory=PLOTTING_FAST_DIRECTORY,
):
    if os.path.exists(plotting_slow_directory):
        print_debug("Deleting folder %s" % plotting_slow_directory)
        shutil.rmtree(plotting_slow_directory)

    if os.path.exists(plotting_fast_directory):
        print_debug("Deleting folder %s" % plotting_fast_directory)
        shutil.rmtree(plotting_fast_directory)


def check_directories_available_space(
    plotting_slow_directory=PLOTTING_SLOW_DIRECTORY,
    plotting_fast_directory=PLOTTING_FAST_DIRECTORY,
    destination_temporary_directory=DESTINATION_TEMPORARY_DIRECTORY,
):
    can_run = True

    if plotting_slow_directory.split(":")[0] == plotting_fast_directory.split(":")[0]:
        try:
            print_debug("plotting directory %s" % plotting_slow_directory)
            drive_available_space_gib = psutil.disk_usage(
                plotting_slow_directory
            ).free / (2 ** 30)
            if drive_available_space_gib < COMBINED_DIR_MIN_AVAILABLE_SPACE:
                can_run = False
        except:
            print_debug(
                "\tError processing plotting directory %s\n" % plotting_slow_directory
            )
    else:
        try:
            print_debug("plotting_slow_directory %s" % plotting_slow_directory)
            drive_available_space_gib = psutil.disk_usage(
                plotting_slow_directory
            ).free / (2 ** 30)
            if drive_available_space_gib < SLOW_DIR_MIN_AVAILABLE_SPACE:
                can_run = False
        except:
            print_debug(
                "\tError processing plotting_slow_directory %s\n"
                % plotting_slow_directory
            )

        try:
            print_debug("plotting_fast_directory %s" % plotting_fast_directory)
            drive_available_space_gib = psutil.disk_usage(
                plotting_fast_directory
            ).free / (2 ** 30)
            if drive_available_space_gib < FAST_DIR_MIN_AVAILABLE_SPACE:
                can_run = False
        except:
            print_debug(
                "\tError processing plotting_fast_directory %s\n"
                % plotting_fast_directory
            )

    try:
        print_debug(
            "destination_temporary_directory %s" % destination_temporary_directory
        )
        drive_available_space_gib = psutil.disk_usage(
            destination_temporary_directory
        ).free / (2 ** 30)
        if drive_available_space_gib < PLOT_FINAL_SIZE_GIB:
            can_run = False
    except:
        print_debug(
            "\tError processing destination_temporary_directory %s\n"
            % destination_temporary_directory
        )

    return can_run


def retrieve_storage_drives_capabilities(
    storage_drives=STORAGE_DRIVES, plot_final_size_gib=PLOT_FINAL_SIZE_GIB
):
    storage_drives_capabilities = []
    total_available_storage_drives_space_gib = 0
    total_number_of_plots = 0
    total_remaining_space_after_plots_gib = 0

    for storage_drive in storage_drives:
        try:
            print_debug("Storage drive %s" % storage_drive)

            drive_available_space_gib = psutil.disk_usage(storage_drive).free / (
                2 ** 30
            )
            drive_number_of_plots = int(drive_available_space_gib / plot_final_size_gib)
            drive_available_space_after_plots_gib = (
                drive_available_space_gib - drive_number_of_plots * plot_final_size_gib
            )
            total_available_storage_drives_space_gib += drive_available_space_gib
            total_remaining_space_after_plots_gib += (
                drive_available_space_after_plots_gib
            )
            total_number_of_plots += drive_number_of_plots

            storage_drives_capabilities.append(
                {
                    "storage_drive": storage_drive,
                    "drive_available_space_gib": drive_available_space_gib,
                    "drive_number_of_plots": drive_number_of_plots,
                    "drive_available_space_after_plots_gib": drive_available_space_after_plots_gib,
                }
            )

            print_debug("\tAvailable space: %.2f GiB" % (drive_available_space_gib))
            print_debug("\tPossible plots on this drive: %d" % drive_number_of_plots)
            print_debug(
                "\tRemaining space after plots: %.2f GiB"
                % drive_available_space_after_plots_gib
            )
            print_debug()
        except:
            print_debug("\tError processing storage drive %s\n" % storage_drive)

    cumulative_capabilities = {
        "total_available_storage_drives_space_gib": total_available_storage_drives_space_gib,
        "total_remaining_space_after_plots_gib": total_remaining_space_after_plots_gib,
        "total_number_of_plots": total_number_of_plots,
    }

    print_debug(
        "Total available space on storage drives: %.2f GiB"
        % total_available_storage_drives_space_gib
    )
    print_debug(
        "Total available space on storage drives after plots: %.2f GiB"
        % total_remaining_space_after_plots_gib
    )
    print_debug("Max amount of plots to make: %d" % total_number_of_plots)
    print_debug()

    return cumulative_capabilities, storage_drives_capabilities


def retrieve_cpu_ram_capabilities(ram_mib_per_thread=RAM_MIB_PER_THREAD):
    cpu_core_count = multiprocessing.cpu_count()
    total_ram_gib = psutil.virtual_memory().total
    max_cpu_parallel_capabilities = cpu_core_count
    max_ram_parallel_capabilities = int(total_ram_gib / ram_mib_per_thread)
    max_calculator_parallel_plotting_processes = min(
        max_cpu_parallel_capabilities, max_ram_parallel_capabilities
    )
    calculator_capabilities = {
        "cpu_core_count": cpu_core_count,
        "total_ram_gib": total_ram_gib,
        "max_calculator_parallel_plotting_processes": max_calculator_parallel_plotting_processes,
    }

    print_debug(
        "This calculator has %d logical cores and %d GiB of RAM"
        % (cpu_core_count, total_ram_gib / 2 ** 30)
    )
    print_debug(
        "This calculator can generate %d plots in parallel from CPU and RAM"
        % max_calculator_parallel_plotting_processes
    )
    print_debug()

    return calculator_capabilities


def generate_command_to_run(
    storage_drives_capabilities,
    cpu_ram_capabilities,
    farmer_key=FARMER_KEY,
    pool_key=POOL_KEY,
    plotting_slow_directory=PLOTTING_SLOW_DIRECTORY,
    plotting_fast_directory=PLOTTING_FAST_DIRECTORY,
    destination_temporary_directory=DESTINATION_TEMPORARY_DIRECTORY,
    madmax_chia_plotter_location=MADMAX_CHIA_PLOTTER_LOCATION,
):
    number_of_plots_to_do = storage_drives_capabilities[0]["total_number_of_plots"]
    max_parallel_threads = cpu_ram_capabilities[
        "max_calculator_parallel_plotting_processes"
    ]

    if max_parallel_threads == 0:
        print_debug("Your calculator cannot run a single plotting process")
        return 0

    print_debug(
        "Given CPU and RAM constraints, this calculator can run %d parallel threads for the plotting\n"
        % max_parallel_threads
    )

    madmax_process_command = "%s -n %d -r %d -t %s -2 %s -d %s -f %s -p %s" % (
        madmax_chia_plotter_location,
        number_of_plots_to_do,
        max_parallel_threads,
        plotting_slow_directory,
        plotting_fast_directory,
        destination_temporary_directory,
        farmer_key,
        pool_key,
    )

    return madmax_process_command


def run(parallel_process):
    subprocess.call("start %s" % parallel_process, shell=True)


if __name__ == "__main__":
    clean_temporary_folders()
    cpu_ram_capabilities = retrieve_cpu_ram_capabilities()
    command_to_run = generate_command_to_run(
        storage_drives_capabilities, cpu_ram_capabilities
    )

    if command_to_run == 0:
        sys.exit(0)

    p = multiprocessing.Process(target=run, args=(command_to_run,))
    p.start()
    p.join()

    while True:
        storage_drives_capabilities = retrieve_storage_drives_capabilities()
        fileList = glob.glob(os.path.join(DESTINATION_TEMPORARY_DIRECTORY, "*.plot"))
        if len(fileList) == 0:
            print_debug(
                "No new plot to move. Checking again in %d seconds" % CHECKING_INTERVAL
            )
            time.sleep(CHECKING_INTERVAL)
        else:
            for f in fileList:
                storage_drives_assignments = sorted(
                    storage_drives_capabilities[1],
                    key=lambda x: x["drive_number_of_plots"],
                    reverse=True,
                )
                destination_folder = storage_drives_assignments[0]["storage_drive"]
                print_debug("Moving plot %s to %s" % (f, destination_folder))
                shutil.move(f, destination_folder)
                print_debug("\tmove done")
