from configparser import ConfigParser
import configparser


class Configuration(ConfigParser):
    def get(self, section, option, *, raw=False, vars=None, fallback=configparser._UNSET):
        if not section:
            section = configparser.DEFAULTSECT

        return ConfigParser.get(self, section, option, raw=raw, vars=vars, fallback=fallback)

    def get_section(self, section):
        """
        Get a new instance of this class that only contains the values for a specific section.
        The values are stored in the 'DEFAULTSECT' section.
        """
        section_config = Configuration()
        config = dict(self.items(section))

        for key in config.keys():
            section_config.set(configparser.DEFAULTSECT, option=key, value=config[key])

        return section_config
