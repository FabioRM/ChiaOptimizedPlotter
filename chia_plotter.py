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
        - CHIA_LOCATION
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
    by you hardware to transfer one plot from a plotting drive to a storage drive. this way you will never have more
    than one transfer at a time and thus shorter periods of waste. rule of thumb:
        USB 3.0 drives: about 10 minutes (PROCESS_INTERVAL_SECONDS = 600)
        USB 2.0 drives: about 40 minutes (PROCESS_INTERVAL_SECONDS = 2400)
"""

import sys, os, time
import multiprocessing, subprocess
import shutil, psutil

# configuration constants. these MUST be configured according to your mining machine, the chia software installed
# and also the ssds and hdds installed
PLOTTING_DRIVES = ["C:/"]  # example ["C:/", "D:/"]
STORAGE_DRIVES = ["D:/"]  # example ["E:/", "F:/", "G:/", "H:/", "I:/"]
CHIA_LOCATION = (
    "%APPDATA%/../Local/chia-blockchain/app-1.1.6/resources/app.asar.unpacked/daemon/"
)
FARMER_KEY = "a3d6fd875db16e7ccc98ffda929779c1abf9ae852674c5ec7de630defa73852894f131620dafc33874408c8e842ad606"
POOL_KEY = "ae6c61298964c91bbf1ab2b37dece103406ce8012b938f0edddd8ed53074790b839e25008587845317fe24fffbfe3182"


# constants - only advanced users should change them
PROCESS_INTERVAL_SECONDS = 0
TEMP_FOLDERS_PREFIX = "chia_plot_temp"
PLOT_TEMP_SIZE_GIB = 239
PLOT_FINAL_SIZE_GIB = 101.3
K_FACTOR = 32
THREADS_PER_PLOT = 2
RAM_GIB_PER_PLOT = 4000


def clean_temporary_folders(
    plotting_drives_list=PLOTTING_DRIVES, temp_folders_prefix=TEMP_FOLDERS_PREFIX
):
    folders_list = []
    for plotting_driver in plotting_drives_list:
        for i in range(256):
            possible_folder = os.path.join(
                plotting_driver, temp_folders_prefix + str(i)
            )
            folders_list.append(possible_folder)

    for folder in folders_list:
        if os.path.exists(folder):
            print("Deleting folder %s" % folder)
            shutil.rmtree(folder)


def retrieve_plotting_drives_capabilities(
    plotting_drives=PLOTTING_DRIVES, plot_temp_size_gib=PLOT_TEMP_SIZE_GIB
):
    plotting_drives_capabilities = []
    max_parallel_plots = 0
    total_available_plotting_drives_space_gib = 0
    total_remaining_plotting_drives_space_after_temp_gib = 0

    for plotting_drive in plotting_drives:
        drive_available_space_gib = psutil.disk_usage(plotting_drive).free / (2 ** 30)
        drive_parallel_plots = int(drive_available_space_gib / plot_temp_size_gib)
        drive_available_space_after_temp_gib = (
            drive_available_space_gib - drive_parallel_plots * plot_temp_size_gib
        )
        total_available_plotting_drives_space_gib += drive_available_space_gib
        max_parallel_plots += drive_parallel_plots
        total_remaining_plotting_drives_space_after_temp_gib += (
            drive_available_space_after_temp_gib
        )

        plotting_drives_capabilities.append(
            {
                "plotting_drive": plotting_drive,
                "total_available_plotting_drives_space_gib": total_available_plotting_drives_space_gib,
                "drive_parallel_plots": drive_parallel_plots,
                "drive_available_space_after_temp_gib": drive_available_space_after_temp_gib,
            }
        )

        print("Plotting drive %s" % plotting_drive)
        print("\tAvailable space: %.2f GiB" % (drive_available_space_gib))
        print("\tParallel plots on this drive: %d" % drive_parallel_plots)
        print(
            "\tRemaining space after temp files: %.2f GiB"
            % drive_available_space_after_temp_gib
        )
        print()

    cumulative_capabilities = {
        "total_available_plotting_drives_space_gib": total_available_plotting_drives_space_gib,
        "total_remaining_plotting_drives_space_after_temp_gib": total_remaining_plotting_drives_space_after_temp_gib,
        "max_parallel_plots": max_parallel_plots,
    }

    print(
        "Total available space on plotting drives: %.2f GiB"
        % total_available_plotting_drives_space_gib
    )
    print(
        "Total available space on plotting drives after temp files: %.2f GiB"
        % total_remaining_plotting_drives_space_after_temp_gib
    )
    print("Max parallel plotting processes: %d" % max_parallel_plots)
    print()

    return cumulative_capabilities, plotting_drives_capabilities


def retrieve_storage_drives_capabilities(
    storage_drives=STORAGE_DRIVES, plot_final_size_gib=PLOT_FINAL_SIZE_GIB
):
    storage_drives_capabilities = []
    total_available_storage_drives_space_gib = 0
    total_number_of_plots = 0
    total_remaining_space_after_temp_gib = 0

    for storage_drive in storage_drives:
        drive_available_space_gib = psutil.disk_usage(storage_drive).free / (2 ** 30)
        drive_number_of_plots = int(drive_available_space_gib / plot_final_size_gib)
        drive_available_space_after_plots_gib = (
            drive_available_space_gib - drive_number_of_plots * plot_final_size_gib
        )
        total_available_storage_drives_space_gib += drive_available_space_gib
        total_remaining_space_after_temp_gib += drive_available_space_after_plots_gib
        total_number_of_plots += drive_number_of_plots

        storage_drives_capabilities.append(
            {
                "storage_drive": storage_drive,
                "drive_available_space_gib": drive_available_space_gib,
                "drive_number_of_plots": drive_number_of_plots,
                "drive_available_space_after_plots_gib": drive_available_space_after_plots_gib,
            }
        )

        print("Storage drive %s" % storage_drive)
        print("\tAvailable space: %.2f GiB" % (drive_available_space_gib))
        print("\tPossible plots on this drive: %d" % drive_number_of_plots)
        print(
            "\tRemaining space after plots: %.2f GiB"
            % drive_available_space_after_plots_gib
        )
        print()

    cumulative_capabilities = {
        "total_available_storage_drives_space_gib": total_available_storage_drives_space_gib,
        "total_remaining_space_after_temp_gib": total_remaining_space_after_temp_gib,
        "total_number_of_plots": total_number_of_plots,
    }

    print(
        "Total available space on storage drives: %.2f GiB"
        % total_available_storage_drives_space_gib
    )
    print(
        "Total available space on storage drives after plots: %.2f GiB"
        % total_remaining_space_after_temp_gib
    )
    print("Total number of possible plots: %d" % total_number_of_plots)
    print()

    return cumulative_capabilities, storage_drives_capabilities


def retrieve_cpu_ram_capabilities(
    threads_per_plot=THREADS_PER_PLOT, ram_gib_per_plot=RAM_GIB_PER_PLOT
):
    cpu_core_count = multiprocessing.cpu_count()
    total_ram_gib = psutil.virtual_memory().total
    max_cpu_parallel_capabilities = int(cpu_core_count / threads_per_plot)
    max_ram_parallel_capabilities = int(total_ram_gib / ram_gib_per_plot)
    max_calculator_parallel_plotting_processes = min(
        max_cpu_parallel_capabilities, max_ram_parallel_capabilities
    )
    calculator_capabilities = {
        "cpu_core_count": cpu_core_count,
        "total_ram_gib": total_ram_gib,
        "max_calculator_parallel_plotting_processes": max_calculator_parallel_plotting_processes,
    }

    print(
        "This calculator has %d logical cores and %d GiB of RAM"
        % (cpu_core_count, total_ram_gib / 2 ** 30)
    )
    print(
        "This calculator can generate %d plots in parallel from CPU and RAM"
        % max_calculator_parallel_plotting_processes
    )
    print()

    return calculator_capabilities


def generate_parallel_processes(
    plotting_drives_capabilities,
    storage_drives_capabilities,
    cpu_ram_capabilities,
    executable_location=CHIA_LOCATION,
    farmer_key=FARMER_KEY,
    pool_key=POOL_KEY,
    k_factor=K_FACTOR,
    threads_per_plot=THREADS_PER_PLOT,
    temp_folder_prefix=TEMP_FOLDERS_PREFIX,
):
    number_of_plots_to_do = storage_drives_capabilities[0]["total_number_of_plots"]
    max_parallel_plots_plotting_devices = plotting_drives_capabilities[0][
        "max_parallel_plots"
    ]
    max_parallel_plots_calculator = cpu_ram_capabilities[
        "max_calculator_parallel_plotting_processes"
    ]
    max_parallel_processes = min(
        max_parallel_plots_plotting_devices, max_parallel_plots_calculator
    )

    if max_parallel_processes == 0:
        print("Your calculator cannot run a single plotting process")
        return 0

    plots_per_process = int(number_of_plots_to_do / max_parallel_processes)
    remaining_plots = int(number_of_plots_to_do % max_parallel_processes)
    print(
        "Given CPU, RAM and plotting space limitations, this calculator can make %d parallel plots"
        % max_parallel_processes
    )
    print()
    single_process_plots = []
    for _ in range(max_parallel_processes):
        single_process_plots.append(plots_per_process)
    for i in range(remaining_plots):
        single_process_plots[i] += 1
    print("Assigned plots per process:", single_process_plots)

    temp_folders = []
    dest_folders = []
    for i in range(max_parallel_processes):
        j = i % len(plotting_drives_capabilities[1])
        k = i % len(storage_drives_capabilities[1])
        temp_folder = os.path.join(
            plotting_drives_capabilities[1][j]["plotting_drive"],
            "%s%d" % (temp_folder_prefix, i),
        )
        dest_folder = storage_drives_capabilities[1][k]["storage_drive"]
        temp_folders.append(temp_folder)
        dest_folders.append(dest_folder)

    parallel_processes_commands = []
    for i in range(max_parallel_processes):
        parallel_process_command = (
            "chia plots create -k %d -n %d -r %d -t %s -d %s -f %s -p %s"
            % (
                k_factor,
                single_process_plots[i],
                threads_per_plot,
                temp_folders[i],
                dest_folders[i],
                farmer_key,
                pool_key,
            )
        )
        parallel_processes_commands.append(parallel_process_command)
        print("Process %d\t%s" % (i, parallel_process_command))

    print()

    return {
        "parallel_processes_commands": parallel_processes_commands,
        "single_process_plots": single_process_plots,
        "temp_folders": temp_folders,
        "dest_folders": dest_folders,
    }


def run(script, executable_location=CHIA_LOCATION):
    print("Launching process: %s" % script)
    # subprocess.call("start TIMEOUT /T 10", shell=True)
    subprocess.call("start %s" % os.path.join(executable_location, script), shell=True)


if __name__ == "__main__":
    clean_temporary_folders()
    plotting_drives_capabilities = retrieve_plotting_drives_capabilities()
    storage_drives_capabilities = retrieve_storage_drives_capabilities()
    cpu_ram_capabilities = retrieve_cpu_ram_capabilities()
    parallel_processes = generate_parallel_processes(
        plotting_drives_capabilities, storage_drives_capabilities, cpu_ram_capabilities
    )

    if parallel_processes == 0:
        sys.exit(0)

    for script in parallel_processes["parallel_processes_commands"]:
        p = multiprocessing.Process(target=run, args=(script,))
        p.start()
        time.sleep(PROCESS_INTERVAL_SECONDS)
    p.join()

    print(
        "\nThe script will now exit, check the processes within their respective shells"
    )

"""
print(plotting_drives_capabilities)
print(storage_drives_capabilities)
print(cpu_ram_capabilities)
print(parallel_processes)
"""
