import imp
import sys

_counter = 1

class Notebook:
    def __init__(self, path=[]):
        global _counter
        
        self.__prefix = "__reinteract" + str(_counter)
        _counter += 1

        self.__path = path
        self.__modules = {}

        self.__root_module = imp.new_module(self.__prefix)
        self.__root_module.path = path
        sys.modules[self.__prefix] = self.__root_module
        
    def set_path(self, path):
        if path != self.__path:
            self.__path = path
            self.__root_module.path = path
            self.__reset_all_modules()

    def __reset_all_modules(self):
        for (name, module) in enumerate(self.__modules):
            del sys.modules[self.__prefix + "." + name]

    def reset_module_by_filename(self, filename):
        for (name, module) in enumerate(self.__modules):
            if module.__filename__ == filename:
                del sys.modules[self.__prefix + "." + name]
                del self.__modules[name]
                return module

    def __find_and_load(self, fullname, name, parent=None, local=None):
        if parent == None:
            assert local == None
            try:
                f, pathname, description = imp.find_module(name, self.__path)
                local = True
            except ImportError:
                f, pathname, description = imp.find_module(name)
                local = False
        else:
            assert local != None
            f, pathname, description = imp.find_module(name, parent.__path__)

        try:
            if local:
                module = imp.load_module(self.__prefix + "." + fullname, f, pathname, description)
                self.__modules[name] = module
            else:
                module = imp.load_module(name, f, pathname, description)

            if parent != None:
                parent.__dict__[name] = module
        finally:
            if f != None:
                f.close()

        return module, local
        
    def __import_recurse(self, names):
        fullname = ".".join(names)
        
        try:
            return self.__modules[fullname], True
        except KeyError:
            pass
        
        try:
            return sys.modules[fullname], False
        except KeyError:
            pass

        if len(names) == 1:
            module, local = self.__find_and_load(fullname, names[-1])
        else:
            parent, local = self.__import_recurse(names[0:-1])
            module, _ = self.__find_and_load(fullname, names[-1], parent=parent, local=local)

        return module, local

    def __ensure_from_list_item(self, fullname, fromname, module, local):
        if fromname == "*": # * inside __all__, ignore
            return
        
        if not isinstance(fromname, basestring):
            raise TypeError("Item in from list is not a string")
        
        try:
            getattr(module, fromname)
        except AttributeError:
            self.__find_and_load(fullname + "." + fromname, fromname, parent=module, local=local)
        
    def do_import(self, name, globals=None, locals=None, fromlist=None, level=None):
        names = name.split('.')
        
        module, local =  self.__import_recurse(names)
        
        if fromlist != None:
            # In 'from a.b import c', if a.b.c doesn't exist after loading a.b, Python
            # will try to load a.b.c as a module
            for fromname in fromlist:
                if fromname == "*":
                    try:
                        all = getattr(module, "__all__")
                        for allname in all:
                            self.__ensure_from_list_item(name, allname, module, local)
                    except AttributeError:
                        pass
                else:
                    self.__ensure_from_list_item(name, fromname, module, local)
                            
            return module
        elif local:
            return self.__modules[names[0]]
        else:
            return sys.modules[names[0]]
