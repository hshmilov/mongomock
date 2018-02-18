import importlib
import sys


def debug_main():
    service_name = sys.argv[1]
    package_name = service_name
    module = importlib.import_module(f"{package_name}.service")
    service_class_name = package_name.replace('_', ' ').title().replace(' ', '')
    SerivceClass = getattr(module, service_class_name)
    service = SerivceClass()

    # Run (Blocking)
    service.start_serve()


if __name__ == '__main__':
    debug_main()
