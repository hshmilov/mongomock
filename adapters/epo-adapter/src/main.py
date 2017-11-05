from epoplugin import EpoPlugin

if __name__ == '__main__':
    # Initialize
    EPO_WRAPPER = EpoPlugin()

    # Run (Blocking)
    EPO_WRAPPER.start_serve()
