import subprocess
import os
import platform

def run_script_in_new_terminal(script_path):
    if platform.system() == "Windows":
        # Adjusting the script path format for Windows
        script_path = os.path.normpath(script_path)
        subprocess.Popen(['start', 'cmd', '/k', f'python {script_path}'], shell=True)
    elif platform.system() == "Darwin":
        subprocess.Popen(['open', '-a', 'Terminal', 'python3', script_path])
    elif platform.system() == "Linux":
        subprocess.Popen(['gnome-terminal', '--', 'python3', script_path])

if __name__ == "__main__":
    current_folder = os.path.dirname(os.path.realpath(__file__))

    # Run scripts in the specified order
    scripts_to_run = [
        'notifyDriver.py',
        'edgeControllerSyncSupport.py',
        'edgeController.py',
        os.path.join('edgeDevices', 'busStopFaker.py'),
        os.path.join('edgeDevices', 'send_buses_onthe_road.py')
    ]

    for script in scripts_to_run:
        script_path = os.path.join(current_folder, script)
        print(f"Running script: {script_path}")
        run_script_in_new_terminal(script_path)

    print("All scripts have been executed.")
