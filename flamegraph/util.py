
import sys
import os

# Super dirty hack due to our vagrant uses 2.7.6 python which
# does not include site.getsitepackages
PREFIXES = [sys.prefix, sys.exec_prefix]
def getsitepackages():
    """Returns a list containing all global site-packages directories
    (and possibly site-python).

    For each directory present in the global ``PREFIXES``, this function
    will find its `site-packages` subdirectory depending on the system
    environment, and will return a list of full paths.
    """
    sitepackages = []
    seen = set()
    for prefix in PREFIXES:
        if not prefix or prefix in seen:
            continue
        seen.add(prefix)

        if sys.platform in ('os2emx', 'riscos'):
            sitepackages.append(os.path.join(prefix, "Lib", "site-packages"))
        elif os.sep == '/':
            sitepackages.append(os.path.join(prefix, "lib",
                                        "python" + sys.version[:3],
                                        "site-packages"))
            sitepackages.append(os.path.join(prefix, "lib", "site-python"))
        else:
            sitepackages.append(prefix)
            sitepackages.append(os.path.join(prefix, "lib", "site-packages"))
        if sys.platform == "darwin":
            # for framework builds *only* we add the standard Apple
            # locations.
            from sysconfig import get_config_var
            framework = get_config_var("PYTHONFRAMEWORK")
            if framework:
                sitepackages.append(
                        os.path.join("/Library", framework,
                            sys.version[:3], "site-packages"))
    # does not get included, and is where most of extra libs (like twistd) are
    sitepackages.append("/opt/osirium/pythonenv/local/lib/python2.7/site-packages")

    sitepackages.append("/mnt/eggs/")
    return sitepackages

def get_threadname():
    import threading
    ident = threading.current_thread().ident
    for th in threading.enumerate():
        if th.ident == ident:
            return th.getName()
    return str(ident)