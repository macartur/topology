# This is the Path to a json file to be preloaded during napp startup.
# This file must have a list of circuits, with their names (or aliases), list
# of hops and their custom properties. For a detailed example, see
# etc/circuits.json.sample
CUSTOM_CIRCUITS_PATH = 'etc/circuits.json'

# Set default values for custom properties, for all single link circuits.  A
# composed circuit property will be the sum of the sub-circuits.  For instance:
# Assume a 3 hops linear circuits: a,b,c. If the circuit a-b has 'weigth' 10,
# and 'b-c' has the weigth 20, then the circuit 'a-c' will have 'weight = 30'.
#
## Example of custom properties:
#   {
#     'weigth': 20,
#     'adm_cost':33
#   }
#
# This applies those values to all single-link circuits, unless those are
# defined in the CUSTOM_CIRCUITS file.
CUSTOM_PROPERTY_DEFAULTS = {
}

# Define here your datapaths custom properties
# Here is a simple example. Please edit as you wish.
CUSTOM_PROPERTY_DPIDS = {
  '00:00:00:00:00:00:00:01': {
      'lat': 0.8,
      'long': 2.2
  },
}

# Set this option to true if you need the topology with bi-directional links
DISPLAY_FULL_DUPLEX_LINKS = True
