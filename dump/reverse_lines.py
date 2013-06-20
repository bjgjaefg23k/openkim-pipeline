import mmap
import os

def tail_iter(filename):
    """Returns last n lines from the filename. No exception handling"""
    size = os.path.getsize(filename)
    with open(filename, "rb") as f:
        # for Windows the mmap parameters are different
        fm = mmap.mmap(f.fileno(), 0, mmap.MAP_SHARED, mmap.PROT_READ)
        try:
            last = size-1
            for i in xrange(size - 1, -1, -1):
                if fm[i] == '\n' or i == -1:
                    yield fm[i+1:last+1]
                    last = i
        finally:
            fm.close()
