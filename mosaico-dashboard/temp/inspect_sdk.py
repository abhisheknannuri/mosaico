import pprint
from collections import Counter, defaultdict

from mosaico_dashboard.gateway.sdk import SdkGateway


def main():
    gateway = SdkGateway(
        host="localhost",
        port=6726,
        api_key=None,
        tls=False,
        tls_cert_path=None,
        connect_timeout=2,
    )

    client = gateway._fresh_client()

    print(client.info())
    print(client._status)
    print(client.list_sequences())
    recordings = gateway.list_recordings()
    print(recordings[0])
    print("=" * 20)
    list_of_streams = []
    list_of_streams = [gateway.list_streams(recording.name) for recording in recordings]
    print(list_of_streams[0])
    print(f"length of list_of_streams: {len(list_of_streams)}")
    for stream in list_of_streams:
        print(len(stream))
        for s in stream:
            print(s.ontology_tag, s.recording)
    ontotogy_tags = defaultdict(Counter)
    for stream in list_of_streams:
        for s in stream:
            ontotogy_tags[s.recording][s.ontology_tag] += 1
    pprint.pprint(ontotogy_tags)


# if __name__==__main__:
#     main()
main()
