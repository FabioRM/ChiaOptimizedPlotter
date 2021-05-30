"""
Fabio Angeletti 2021
fabio.angeletti89@gmail.com

HOW TO USE:
    adapt CHIA_LOCATION, FARMER_KEY, POOL_KEY
    run the script
    done
"""

import sys
import os
import time
import psutil
import multiprocessing
import shutil

PLOT_TEMP_SIZE_GIB = 239
PLOT_FINAL_SIZE_GIB = 101.3

CHIA_LOCATION = (
    "%APPDATA%/../Local/chia-blockchain/app-1.1.6/resources/app.asar.unpacked/daemon/"
)
FARMER_KEY = "a3d6fd875db16e7ccc98ffda929779c1abf9ae852674c5ec7de630defa73852894f131620dafc33874408c8e842ad606"
POOL_KEY = "ae6c61298964c91bbf1ab2b37dece103406ce8012b938f0edddd8ed53074790b839e25008587845317fe24fffbfe3182"
TEMP_FOLDERS_PREFIX = "chia_plot_temp"
K_FACTOR = 32
THREADS_PER_PLOT = 2
RAM_GIB_PER_PLOT = 4000

PLOTTING_DRIVES = ["C:/", "D:/"]
STORAGE_DRIVES = ["E:/"]


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
        "Total available space on storage drives after temp files: %.2f GiB"
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
    os.system(os.path.join(executable_location, script))


if __name__ == "__main__":
    clean_temporary_folders()
    plotting_drives_capabilities = retrieve_plotting_drives_capabilities()
    storage_drives_capabilities = retrieve_storage_drives_capabilities()
    cpu_ram_capabilities = retrieve_cpu_ram_capabilities()
    parallel_processes = generate_parallel_processes(
        plotting_drives_capabilities, storage_drives_capabilities, cpu_ram_capabilities
    )

    for script in parallel_processes["parallel_processes_commands"]:
        p = multiprocessing.Process(target=run, args=(script,))
        p.start()
    p.join()

"""
print(plotting_drives_capabilities)
print(storage_drives_capabilities)
print(cpu_ram_capabilities)
print(parallel_processes)
"""
