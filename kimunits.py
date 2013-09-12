#! /usr/bin/env python
""" Simple wrapper for udunits2-bin for converting arbitrary units to SI units """
VERSION = 0.3

import subprocess
import re
import warnings
warnings.simplefilter("ignore")

from logger import logging
logger = logging.getLogger("pipeline").getChild("kimunits")
logger.setLevel(logging.DEBUG)

class UnitConversion(Exception):
    """ Class for unit conversion errors """

_output_expression_default = re.compile("You have: You want:     "
        "(?:(?P<value>(?:[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)) )?"
        "(?P<unit>\S+)",)

_output_expression_convert = re.compile("You have: You want:     "
        ".*?= " #with original stuff
        "(?:(?P<value>(?:[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)) )?"
        "(?P<unit>\S+)",)

def convert_udunits2(from_value,from_unit,wanted_unit=None, suppress_unit=False):
    """ Wraps udunits2 through expect like behavior """
    # first line of input
    ZERO = False
    if float(from_value) == 0:
        # special Zero handling
        if from_unit != '1':
            warnings.warn("""Found a 0, udunits2 breaks,
            so we are assuming that this is not a non-zero based conversion like temperature""")
        ZERO = True
        from_value = 1.
    line1 = str(from_value) + " " + str(from_unit)
    # second line of input
    line2 = str(wanted_unit) if wanted_unit else ' '
    inp = "\n".join((line1,line2))
    # Create subprocess with ascii encoding
    process = subprocess.Popen(['udunits2','-A'],
            bufsize=1000,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
    # get output
    stdout,stderr = process.communicate(inp)
    # check for errors
    if len(stderr.splitlines())>1:
        raise UnitConversion("\n".join(stderr.splitlines()[1:]))

    # find matches
    if not wanted_unit:
        matches = _output_expression_default.match(stdout).groupdict(None)
    else:
        matches = _output_expression_convert.match(stdout).groupdict(None)
    if ZERO:
        out = ( 0.0 , matches['unit'] )
    else:
        out = ( float( ( matches['value']  or 1.0 )) , matches['unit'])
    if suppress_unit:
        return out[0]
    return out


_units_output_expression = re.compile("(?P<value>(?:[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?))"
        "(?: (?P<unit>.+))?",)

def convert_units(from_value, from_unit, wanted_unit=None, suppress_unit=False):
    """ Works with 'units' utility """
    from_value = str(from_value)
    from_unit = str(from_unit)
    try:
        if wanted_unit:
            output = subprocess.check_output(['units','-qt1',' ' + ' '.join((from_value, from_unit)),wanted_unit])
        else:
            output = subprocess.check_output(['units','-qt1',' ' + ' '.join((from_value, from_unit))])
    except subprocess.CalledProcessError as e:
        raise UnitConversion(e)

    matches = _units_output_expression.match(output).groupdict(None)
    out = (float(matches['value']), matches['unit'] or wanted_unit)

    if suppress_unit:
        return out[0]
    return out


def convert_cfunits(from_value, from_unit, wanted_unit=None, suppress_unit=False):
    """ Use the cfunits-python package to handle the interaction with udunits2 """
    try:
        from cfunits import Units
    except ImportError:
        raise Exception("cfunits option relies on cfunits-python package")
    ZERO = False
    if float(from_value) == 0:
        # special Zero handling
        if from_unit != '1':
            warnings.warn("""Found a 0, udunits2 breaks,
            so we are assuming that this is not a non-zero based conversion like temperature""")
        ZERO = True
        from_value = 1.
    if wanted_unit:
        return Units.conform(from_value, Units(from_unit), Units(wanted_unit))
    out = Units(" ".join((str(from_value), from_unit))).format()
    split_out = out.split(' ')
    if len(split_out) == 1:
        out = (1., split_out[0])
    else:
        if ZERO:
            out = (0.0, split_out[1])
        else:
            out = (float(split_out[0]), split_out[1])

    if suppress_unit:
        return out[0]
    return out

#Set default behavior
convert = convert_units

def convert_list( x , from_unit, to_unit=None, convert=convert):
    """ Thread conversion over a list, or list of lists """
    # Need a list for scoping reasons
    logger.debug("Attempting to convert <%r> from <%r> to <%r>.", x, from_unit, to_unit)
    known_out = [None]

    # Constant shortcut
    if from_unit in ( 1, 1.0, '1' ):
        known_out[0] = '1'

    def convert_inner( x ):
        if isinstance(x, (list,tuple)):
            return type(x)( convert_inner(z ) for z in x )
        else:
            if known_out[0] == '1':
                return float(x)
            elif known_out[0]:
                out = convert( x, from_unit, to_unit, suppress_unit=True )
                return out
            else:
                out = convert( x, from_unit, to_unit )
                known_out[0] = out[1]
                return float(out[0])
    output = convert_inner( x )
    logger.debug("Obtained %r <%r> = %r <%r>.", x, from_unit, output, known_out[0])
    return ( output, known_out[0] )


def add_si_units(doc, convert=convert):
    """ Given a document, add all of the appropriate si-units fields """
    if isinstance(doc,dict):
        #kludge for bad formatting
        if 'source-unit' in doc or 'source-units' in doc:
            #we've found a place to add
            assert 'source-value' in doc, "Badly formed doc"
            o_value = doc['source-value']
            # check for bad name
            o_unit = doc.get('source-unit',None) or doc['source-units']
            value, unit = convert_list( o_value, o_unit , convert=convert)
            si_dict = {"si-unit": unit, "si-value": value }
            doc = doc.copy()
            doc.update(si_dict)
            return doc
        else:
            # recurse
            return type(doc)( (key, add_si_units(value)) for key,value in doc.iteritems() )

    if isinstance(doc, (list,tuple)):
        return type(doc)( add_si_units(x) for x in doc )

    return doc

