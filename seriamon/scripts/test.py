from seriamon.filter import FilterManager
from seriamon.component import SeriaMonPort

def run(tgt: SeriaMonPort, repeat:int = 1):
    log("tgt={}, repeat={}".format(tgt, repeat))
    repeat = int(repeat)
    log("Console is {}".format(tgt.getSource().getComponentName()))

    for count in range(repeat):
        log("=========================")
        log("{:04}".format(count))
        log("=========================")

        prompt='PROMPT>'
        for line in tgt.command("PS1='{}'\n".format(prompt), prompt, timeout=10):
            log("| {}".format(line))
        for line in tgt.command("uname -a\n", prompt, timeout=10):
            log("| {}".format(line))
        for line in tgt.command("ls /foo/bar\n", prompt, timeout=10):
            log("| {}".format(line))
