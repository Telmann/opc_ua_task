#include "open62541.h"

#include <stdlib.h>
#include <time.h>
#include <string.h>
#include <stdio.h>
#include <windows.h>

#define MAX_TAGS 10000

typedef enum { TYPE_DOUBLE, TYPE_INT32, TYPE_BOOLEAN, TYPE_BYTESTRING, TYPE_XMLELEMENT } TagType; 

typedef struct {
    UA_NodeId nodeId;
    TagType type;
} TagEntry;

static TagEntry tags[MAX_TAGS];
static size_t tagCount = 0;

static TagType
randomTagType() {
    int r = rand() % 5; // 3;
    return (TagType)r;
}

static void
addVariable(UA_Server *server, UA_NodeId parentNodeId, const char *name, int index) {
    TagType type = randomTagType();
    char browseName[64];
    snprintf(browseName, sizeof(browseName), "%s_tag%d", // 
        type == TYPE_DOUBLE ? "Double" :
        type == TYPE_INT32 ? "Int" :
        type == TYPE_BOOLEAN ? "Boolean" : 
        type == TYPE_BYTESTRING ? "ByteString" :
        "XmlElement",
             index);

    UA_VariableAttributes attr = UA_VariableAttributes_default;

    switch(type) { // 
        case TYPE_DOUBLE: {
            UA_Double val = 0.0;
            UA_Variant_setScalar(&attr.value, &val, &UA_TYPES[UA_TYPES_DOUBLE]);
            break;
        }
        case TYPE_INT32: {
            UA_Int32 val = 0;
            UA_Variant_setScalar(&attr.value, &val, &UA_TYPES[UA_TYPES_INT32]);
            break;
        }
        case TYPE_BOOLEAN: {
            UA_Boolean val = false;
            UA_Variant_setScalar(&attr.value, &val, &UA_TYPES[UA_TYPES_BOOLEAN]);
            break;
        }
        case TYPE_BYTESTRING: {
            UA_ByteString val = UA_BYTESTRING("0"); 
            UA_Variant_setScalar(&attr.value, &val, &UA_TYPES[UA_TYPES_BYTESTRING]);
            break;
        }
        case TYPE_XMLELEMENT: {
            UA_String val = UA_STRING("<value>random</value>"); 
            UA_Variant_setScalar(&attr.value, &val, &UA_TYPES[UA_TYPES_XMLELEMENT]);
            break;
        }
    }

    attr.displayName = UA_LOCALIZEDTEXT("en-US", browseName);
    attr.accessLevel = UA_ACCESSLEVELMASK_READ | UA_ACCESSLEVELMASK_WRITE;

    UA_NodeId varNodeId;
    UA_Server_addVariableNode(
        server, UA_NODEID_NULL, parentNodeId, UA_NODEID_NUMERIC(0, UA_NS0ID_HASCOMPONENT),
        UA_QUALIFIEDNAME(2, browseName),
        UA_NODEID_NUMERIC(0, UA_NS0ID_BASEDATAVARIABLETYPE), attr, NULL, &varNodeId);

    tags[tagCount].nodeId = varNodeId;
    tags[tagCount].type = type;
    tagCount++;
}

int main(int argc, char **argv) {
    // int numTags = 1000;
    int numTags = atoi(argv[1]);
    if(numTags > MAX_TAGS || numTags <= 0) {
        printf("Please specify a tag count between 1 and %d\n", MAX_TAGS);
        return 1;
    }

    srand((unsigned)time(NULL));

    UA_Server *server = UA_Server_new();
    UA_ServerConfig *config = UA_Server_getConfig(server);
    UA_ServerConfig_setDefault(config);

    config->applicationDescription.applicationUri =
        UA_STRING_ALLOC("urn:open62541.example.server");

    UA_String_clear(&config->endpoints[0].endpointUrl); 

    config->endpoints[0].endpointUrl =
        UA_STRING_ALLOC("opc.tcp://0.0.0.0:4840/freeopcua/server/");

    const char *uri = "http://examples.freeopcua.github.io";
    UA_UInt16 nsIndex = UA_Server_addNamespace(server, uri);

    UA_ObjectAttributes oAttr = UA_ObjectAttributes_default;
    oAttr.displayName = UA_LOCALIZEDTEXT("en-US", "MyObject");

    UA_NodeId myObjectNodeId;
    UA_Server_addObjectNode(
        server, UA_NODEID_NULL, UA_NODEID_NUMERIC(0, UA_NS0ID_OBJECTSFOLDER),
        UA_NODEID_NUMERIC(0, UA_NS0ID_ORGANIZES), UA_QUALIFIEDNAME(nsIndex, "MyObject"),
        UA_NODEID_NUMERIC(0, UA_NS0ID_BASEOBJECTTYPE), oAttr, NULL, &myObjectNodeId);

    for(int i = 0; i < numTags; ++i) {
        addVariable(server, myObjectNodeId, "tag", i);
    }

    UA_Boolean running = true;
    UA_StatusCode retval = UA_Server_run_startup(server);

    while(running) {
        for(size_t i = 0; i < tagCount; ++i) {
            switch(tags[i].type) {
                case TYPE_DOUBLE: { // 
                    UA_Double val = ((double)rand() / RAND_MAX) * 149.55 + 1.6;
                    UA_Variant value;
                    UA_Variant_setScalar(&value, &val, &UA_TYPES[UA_TYPES_DOUBLE]);
                    UA_Server_writeValue(server, tags[i].nodeId, value);
                    break;
                }
                case TYPE_INT32: {
                    UA_Int32 val = rand() % 150 + 1;
                    UA_Variant value;
                    UA_Variant_setScalar(&value, &val, &UA_TYPES[UA_TYPES_INT32]);
                    UA_Server_writeValue(server, tags[i].nodeId, value);
                    break;
                }
                case TYPE_BOOLEAN: {
                    UA_Boolean val = rand() % 2;
                    UA_Variant value;
                    UA_Variant_setScalar(&value, &val, &UA_TYPES[UA_TYPES_BOOLEAN]);
                    UA_Server_writeValue(server, tags[i].nodeId, value);
                    break;
                }
                case TYPE_BYTESTRING: { //
                    UA_ByteString val;
                    UA_ByteString_allocBuffer(&val, 1);  
                    val.data[0] = rand() % 256;          
                    UA_Variant value;
                    UA_Variant_setScalar(&value, &val, &UA_TYPES[UA_TYPES_BYTESTRING]);
                    UA_Server_writeValue(server, tags[i].nodeId, value);
                    UA_ByteString_clear(&val);
                    break;
                }
                case TYPE_XMLELEMENT: {
                    char xml[64];
                    snprintf(xml, sizeof(xml), "<result>%d</result>", rand() % 151);
                    UA_String val = UA_STRING_ALLOC(xml);
                    UA_Variant value;
                    UA_Variant_setScalar(&value, &val, &UA_TYPES[UA_TYPES_XMLELEMENT]);
                    UA_Server_writeValue(server, tags[i].nodeId, value);
                    UA_String_clear(&val);
                    break;
                }
            }
        }
        Sleep(250);
        UA_Server_run_iterate(server, true);
    }
    // printf("pause");
    UA_Server_run_shutdown(server);
    UA_Server_delete(server);
    return retval == UA_STATUSCODE_GOOD ? EXIT_SUCCESS : EXIT_FAILURE;
}
