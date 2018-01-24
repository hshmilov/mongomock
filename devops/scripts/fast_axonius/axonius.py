def _fast_axonius(line):
    from devops.scripts.fast_axonius.fast_axonius import fast_axonius

    ax = fast_axonius()
    get_ipython().user_ns['ax'] = ax
    return ax


get_ipython().register_magic_function(_fast_axonius, magic_name='fastAxonius')
