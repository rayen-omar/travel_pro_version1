# -*- coding: utf-8 -*-
# Mixins (doivent être importés en premier)
from . import mixins

# Modèles principaux
from . import company
from . import member
from . import reservation
from . import service
from . import travel
from . import credit

# Facturation
from . import purchase
from . import invoice
from . import invoice_client
from . import withholding
from . import purchase_travel
from . import purchase_report

# Caisse et POS
from . import pos
from . import cash_register
from . import cash_register_operation

# Extensions modèles Odoo
from . import partner