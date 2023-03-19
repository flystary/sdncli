import os
import random
import svxutil

dnsmasq_conf_path = '/etc/dnsmasq.d'


def write_dnsmasq_tmpfile(lines):
    tmp_file = '%s/dnsmasq.tmp.%s' % (dnsmasq_conf_path, random.randint(0, 10000))
    fp = open(tmp_file, 'w')
    for line in lines:
        fp.write(line + '\n')

    fp.flush()
    fp.close()

    status = svxutil.get_cmd_exitcode('dnsmasq --test')
    if status == 0:
        return tmp_file

    if os.path.exists(tmp_file):
        os.remove(tmp_file)
    return False

    # absolute_path = filename if filename.startswith('/') else '%s/%s' % (dnsmasq_conf_path, filename)
    # os.rename(tmp_file, absolute_path)



def remove_dnsmasq_conf(filename):
    absolute_path = filename if filename.startswith('/') else '%s/%s' % (dnsmasq_conf_path, filename)

    if os.path.exists(absolute_path):
        os.remove(absolute_path)

