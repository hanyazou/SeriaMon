from seriamon.runtime import ScriptRuntime as rt

def run(tgt: rt.Port, repeat: int = 1):
    rt.log("tgt={}, repeat={}".format(tgt, repeat))
    rt.log("target is {}".format(tgt.getSource().getComponentName()))

    tgt.setPattern('.*PROMPT>')
    tgt.setTimeout(rt.deadline(7))
    for count in range(repeat):
        rt.log("=========================")
        rt.log("{:04}".format(count))
        rt.log("=========================")

        tgt.command("PS1='PROMPT>'\n")
        tgt.command("uname -a\n")
        tgt.command("ls /foo/bar\n")
