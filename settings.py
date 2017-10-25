# This is the Path to a json file to be preloaded during napp startup.
# This file must have a list of circuits, with their names (or aliases), list
# of hops and their custom properties. For a detailed example, see
# etc/circuits.json.sample
CUSTOM_CIRCUITS_PATH = 'etc/circuits.json'

# Set default values for custom properties, for all single link circuits.  A
# composed circuit property will be the sum of the sub-circuits.  For instance:
# Assume a 3 hops linear circuits: a,b,c. If the circuit a-b has 'weight' 10,
# and 'b-c' has the weight 20, then the circuit 'a-c' will have 'weight = 30'.
#
## Example of custom properties:
#   {
#     'weight': 20,
#     'adm_cost':33
#   }
#
# This applies those values to all single-link circuits, unless those are
# defined in the CUSTOM_CIRCUITS file.
CUSTOM_PROPERTY_DEFAULTS = {
}

# Set this option to true if you need the topology with bi-directional links
DISPLAY_FULL_DUPLEX_LINKS = True
