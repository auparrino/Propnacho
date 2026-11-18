from .zonaprop import Zonaprop
from .argenprop import Argenprop
from .mercadolibre import MercadoLibre

FUENTES = {f.nombre: f for f in (Zonaprop(), Argenprop(), MercadoLibre())}
