def plugin_base_instance() -> 'PluginBase':
    """
    Returns the current PluginBase instance, helps for recursive imports reduction
    """
    from axonius.plugin_base import PluginBase
    return PluginBase.Instance
