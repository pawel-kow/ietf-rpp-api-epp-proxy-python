"""The handlers of the API, by operationId: connexion resolves them as attributes of this package (rpp.http.app)."""
from rpp.handlers.contact.contact_handlers import (
    contacts_create, contacts_delete, contacts_read, contacts_update, contacts_updatePartial,
    contacts_availabilityHead, contacts_availability
)
from rpp.handlers.contact.contact_transfer_handlers import (
    contactTransferProcesses_transferCreate, contactTransferProcesses_transferRead,
    contactTransferProcesses_transferDelete, contactTransferProcesses_transferApprove,
    contactTransferProcesses_transferReject
)
from rpp.handlers.domain.domain_handlers import (
    domainNames_availabilityHead, domainNames_availability, domainNames_create, domainNames_delete,
    domainNames_read, domainNames_updatePartial, domainNames_update, domainNameRenewProcesses_renewCreate,
    domainNameRestoreProcesses_create, domainNameRestoreProcesses_update, domainNameRestoreProcesses_updatePartial,
    domainNameRestoreProcesses_read
)
from rpp.handlers.domain.domain_transfer_handlers import (
    domainNameTransferProcesses_transferCreate, domainNameTransferProcesses_transferRead,
    domainNameTransferProcesses_transferDelete, domainNameTransferProcesses_transferApprove,
    domainNameTransferProcesses_transferReject
)
from rpp.handlers.host.host_handlers import (
    hosts_availabilityHead, hosts_availability, hosts_create, hosts_read, hosts_update, hosts_updatePartial,
    hosts_delete
)
from rpp.handlers.message.message_handlers import messages_query, messages_read, messages_delete, messages_create
from rpp.handlers.discovery import discovery_read
