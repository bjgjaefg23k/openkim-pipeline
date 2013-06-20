from ConfigParser import ConfigParser

def configtojson(flname):
    c = ConfigParser()
    c.optionxform = str
    c.read(flname)
    data = {}
    for section in c.sections():
        data.update(dict(c.items(section)))
    return data


def eatfile(flname):
    out = {}

    with open(flname) as f:
        guys = []
        key = None
        for line in f:
            if line.startswith("#"):
                continue
            if ":" in line:
                if guys:
                    out[key] = guys
                    guys = []
                    key = None
                if ":=" in line:
                    key,value = line.split(":=")
                    out[key.lower().strip()] = value.strip()
                else:
                    key = line.lower().strip().strip(":")
                    guys = []
            else:
                if line.strip():
                    guys.append(line.strip())
    return out

