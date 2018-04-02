To install, add an 'axonius.pth' file to site-packages (so it can be loaded):

    <cortex_path>/axonius-libs/src/libs/axonius-py<br>
    <cortex_path>/testing<br>
    <cortex_path>

and put the following code inside an 'axonius.py' file under .ipython/profile_default/startup

    def _fast_axonius(line):
        from devops.scripts.fast_axonius.fast_axonius import fast_axonius
        
        ax = fast_axonius()
        get_ipython().user_ns['ax'] = ax
        return ax
    
    get_ipython().register_magic_function(_fast_axonius, magic_name='fastAxonius')

and write fast + TAB to iPython and press ENTER

> you may use the provided install.py that does exactly that.

example usage:

    In [1]: %fastAxonius
    Out[1]: use variable 'ax'
    In [2]: ax.sentinelone.is_up()
    Out[2]: True
    In [3]: ax.sentinelone.set_client()  # sets the creds for sentinelone adapter