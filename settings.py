# This is the Path to a json file to be preloaded during napp startup.
# This file must have a list of circuits, with their names (or aliases), list
# of hops and their custom properties. For a detailed example, see
# etc/circuits.json.sample
CUSTOM_CIRCUITS_PATH = 'etc/circuits.json'

# Set default values for custom properties, for all single link circuits.
# Example:
#{
#   'weigth': 20,
#   'adm_cost':33
#}
#
# This applies those values to all single-link circuits, unless those are
# defined in the CUSTOM_CIRCUITS file.
CUSTOM_PROPERTY_DEFAULTS = {
}

# Set this option to true if you need the topology with bi-directional links
DISPLAY_FULL_DUPLEX_LINKS = True
