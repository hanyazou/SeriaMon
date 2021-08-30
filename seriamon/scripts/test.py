from seriamon.runtime import ScriptRuntime as rt

def run(tgt: rt.Port, repeat: int = 1):
    rt.log("tgt={}, repeat={}".format(tgt, repeat))
    rt.log("target is {}".format(tgt.getSource().getComponentName()))

    for count in range(repeat):
        rt.log("=========================")
        rt.log("{:04}".format(count))
        rt.log("=========================")

        prompt='.*PROMPT>'
        for line in tgt.command("PS1='PROMPT>'\n", prompt, timeout=10):
            rt.log("| {}".format(line))
        for line in tgt.command("uname -a\n", prompt, timeout=10):
            rt.log("| {}".format(line))
        for line in tgt.command("ls /foo/bar\n", prompt, timeout=10):
            rt.log("| {}".format(line))
