import subprocess
import xmltodict
import pprint
import os
import psutil
import shutil


class SystemStats:
    def __init__(self):
        pass

    def get_gpu_info(self):
        try:
            result = subprocess.run(
                ["nvidia-smi", "-x", "-q"], capture_output=True, text=True
            )

            if result.returncode != 0:
                # If the command failed, raise an exception
                raise Exception("nvidia-smi failed: " + result.stderr)

            # Parse the XML output
            my_dict = xmltodict.parse(result.stdout)
        except:
            print("working without GPU, loading placeholder file")
            file = "nvidia_example.xml"
            # file = "nvidia-multi.xml"
            with open(file) as f:
                my_dict = xmltodict.parse(f.read())

        if int(my_dict["nvidia_smi_log"]["attached_gpus"]) > 1:
            gpu_info = []
            for g in my_dict["nvidia_smi_log"]["gpu"]:
                ginfo = {
                    key: round(float(value.split()[0]) / 1024, 2)
                    for key, value in g["fb_memory_usage"].items()
                }
                ginfo["gpu_pct_free"] = (ginfo["free"] / ginfo["total"]) * 100
                ginfo["gpu_pct_used"] = (ginfo["used"] / ginfo["total"]) * 100
                ginfo["gpu_name"] = g["product_name"]
            gpu_info.append(gi)
        elif int(my_dict["nvidia_smi_log"]["attached_gpus"]) == 1:
            ginfo = {
                key: round(float(value.split()[0]) / 1024, 2)
                for key, value in my_dict["nvidia_smi_log"]["gpu"][
                    "fb_memory_usage"
                ].items()
            }
            ginfo["gpu_pct_free"] = (ginfo["free"] / ginfo["total"]) * 100
            ginfo["gpu_pct_used"] = (ginfo["used"] / ginfo["total"]) * 100
            ginfo["gpu_name"] = my_dict["nvidia_smi_log"]["gpu"]["product_name"]
            gpu_info = [ginfo]
        else:
            gpu_info = []

        return gpu_info

    def get_system_usage(self):
        # Memory
        memory_info = psutil.virtual_memory()
        memory_total = round(memory_info.total / (1024.0**3), 2)  # Convert to GB
        memory_used = round(memory_info.used / (1024.0**3), 2)  # Convert to GB
        memory_free = memory_total - memory_used

        # Disk
        disk_info = shutil.disk_usage("/")
        disk_total = round(disk_info.total / (1024.0**3))  # Convert to GB
        disk_used = round(disk_info.used / (1024.0**3))  # Convert to GB
        disk_free = disk_total - disk_used

        # System load
        system_load = round(os.getloadavg()[0], 2)  # Get 1-minute load average

        # CPU utilization
        cpu_utilization = psutil.cpu_percent(interval=0.5)

        # Swap usage
        swap_info = psutil.swap_memory()
        swap_used = round(swap_info.used / (1024.0**3), 2)  # Convert to GB

        return {
            "memory_used": memory_used,
            "memory_total": memory_total,
            "memory_free": memory_free,
            "memory_pct_free": (memory_free / memory_total) * 100,
            "memory_pct_used": (memory_used / memory_total) * 100,
            "disk_used": disk_used,
            "disk_total": disk_total,
            "disk_free": disk_free,
            "disk_pct_free": (disk_free / disk_total) * 100,
            "disk_pct_used": (disk_used / disk_total) * 100,
            "system_load": system_load,
            "cpu_utilization": cpu_utilization,
            "swap_usage": swap_used,
        }

    def collect_system_stats(self):
        try:
            system_stats = self.get_system_usage()
        except Exception as e:
            print(f"Error loading system stats: {e}")
            system_stats = {}
        try:
            system_stats["gpu_info"] = self.get_gpu_info()
        except Exception as e:
            print(f"Error loading GPU stats: {e}")

        return system_stats
