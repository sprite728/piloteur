import json
import logging
import subprocess
import os.path
import os
import operator
import time
import psutil
import uptime
import datetime
import traceback
import ntplib

listdirs = lambda dirname: [os.path.join(dirname, x)
                for x in os.listdir(dirname)
                if os.path.isdir(os.path.join(dirname, x))]

listfiles = lambda dirname: [os.path.join(dirname, x)
                for x in os.listdir(dirname)
                if os.path.isfile(os.path.join(dirname, x))]

def get_device(path):
    output = subprocess.check_output(["df", path])
    device, size, used, available, percent, mountpoint = \
        output.split("\n")[1].split()
    return device


class Syncer():
    def __init__(self, config):
        self.config = config

        logging.basicConfig(format=self.config['log_format'])
        self.log = logging.getLogger('HUB')
        if os.environ.get('DEBUG'):
            self.log.setLevel(logging.DEBUG)
        else:
            self.log.setLevel(logging.INFO)

        self.log.debug('Loaded config: %s', self.config)

        self.DATA_PATH = os.path.expanduser(self.config['data_path'])
        self.LOGS_PATH = os.path.expanduser(self.config['logs_path'])

        self.LOG_HOUR = datetime.datetime.now().strftime('%Y-%m-%d-%H')

    # def run_remote_command(self, command):
    #     ssh_cmd = ["ssh", "-i", self.config['keyfile_path']]
    #     ssh_cmd += ["%s@%s" % (self.config['remoteuser'], self.config['remotehost'])]
    #     ssh_cmd += [command]

    #     self.log.info('Running remote command "%s"', command)
    #     subprocess.check_call(ssh_cmd)

    def run(self):
        self.log.info('---')
        self.start_time = time.time()

        try:
            # Maybe running rsync two times might have to be reconsidered
            success = self.sync(self.DATA_PATH, self.config['remote_data_path'])
            success &= self.sync(self.LOGS_PATH, self.config['remote_logs_path'])
        except:
            traceback.print_exc()
        else:
            if success: self.after_success()

        self.monitor()
        self.timesync()

    def sync(self, local_path, remote_path):
        rsync_cmd = ["rsync", "-avz", "--append"]
        rsync_cmd += ["--timeout", "5"]
        rsync_cmd += ["-e", 'ssh -i %s' % self.config['keyfile_path']]

        rsync_cmd += [local_path]
        rsync_cmd += ["%s@%s:%s" % (self.config['remoteuser'],
            self.config['remotehost'], remote_path)]

        self.log.debug('rsync command line: %s', rsync_cmd)

        self.log.info('Starting rsync %s -> %s...', local_path, remote_path)
        ecode = subprocess.call(rsync_cmd)
        if ecode == 0:
            self.log.info('rsync finished successfully.')
            return True
        else:
            self.log.error('rsync exited with status %i', ecode)
            return False

    def after_success(self):
        sensor_kind_folders = listdirs(self.DATA_PATH)
        for sensor_kind_folder in sensor_kind_folders:
            sensor_folders = listdirs(sensor_kind_folder)
            for sensor_folder in sensor_folders:
                self.prune_old(sensor_folder)

        self.prune_old(self.LOGS_PATH)
        log_modules_folders = listdirs(self.LOGS_PATH)
        for log_modules_folder in log_modules_folders:
            self.prune_old(log_modules_folder)

    def prune_old(self, sensor_folder):
        # Please note the (unavoidable?) race condition between
        # os.path.getmtime and os.remove

        files = [(name, os.path.getmtime(name))
            for name in listfiles(sensor_folder)]
        files.sort(key=operator.itemgetter(1), reverse=True)

        self.log.debug(files)

        # Save the two most recent files
        files = files[2:]

        # Filter out still unsynced files
        files = [(f, t) for f, t in files if t < self.start_time]

        for f, t in files:
            self.log.info('Pruning old file %s modified on %f'
                % (f, t))
            os.remove(f)

    def monitor(self):
        MONITOR_PATH = os.path.join(self.LOGS_PATH, "monitor/monitor-log.%s.json" % self.LOG_HOUR)

        data = {}

        data["uptime"] = uptime.uptime()
        data["timestamp"] = datetime.datetime.now().isoformat()
        data["cpu_percent"] = psutil.cpu_percent(0)
        data["free_memory"] = psutil.virtual_memory().available
        data["free_disk"] = psutil.disk_usage(self.DATA_PATH).free

        device = os.path.basename(get_device(self.DATA_PATH))
        iostat = psutil.disk_io_counters(perdisk=True)[device]
        data["iostat"] = {
            "read_bytes": iostat.read_bytes,
            "write_bytes": iostat.write_bytes,
            "read_count": iostat.read_count,
            "write_count": iostat.write_count
        }

        self.log.debug(data)

        with open(MONITOR_PATH, 'a') as f:
            json.dump(data, f, sort_keys=True)
            f.write('\n')

    def timesync(self):
        TIMESYNC_PATH = os.path.join(self.LOGS_PATH, "timesync/timesync-log.%s.csv" % self.LOG_HOUR)

        self.log.info('doing a NTP request...')

        r = ntplib.NTPClient().request('us.pool.ntp.org')
        local = datetime.datetime.utcfromtimestamp(r.dest_time)
        remote = datetime.datetime.utcfromtimestamp(
            r.tx_time - r.delay / 2)

        with open(TIMESYNC_PATH, 'a') as f:
            f.write('%s,%s,%f\n' %(local.isoformat(), remote.isoformat(),
                r.offset))



def main():
    with open('config.json') as f:
        config = json.load(f)

    s = Syncer(config)
    s.run()

if __name__ == '__main__':
    main()
