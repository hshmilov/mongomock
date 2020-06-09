import pluginMetaJson from './plugin_meta.json';

export const pluginMeta = {
  ...pluginMetaJson,
};

export const pluginTitlesToNames = Object.keys(pluginMeta).reduce((map, obj) => {
  map[pluginMeta[obj].title] = obj
  return map
}, {})
