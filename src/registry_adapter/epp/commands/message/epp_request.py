from registry_adapter.epp.xml.generated.epp_1_0 import CommandType, Epp, PollOpType, PollType


def poll_request(rpp_cl_trid: str) -> Epp:
    return Epp(command=CommandType(poll=PollType(op=PollOpType.REQ), cl_trid=rpp_cl_trid))


def poll_ack(message_id: str, rpp_cl_trid: str) -> Epp:
    return Epp(command=CommandType(poll=PollType(op=PollOpType.ACK, msg_id=message_id), cl_trid=rpp_cl_trid))
