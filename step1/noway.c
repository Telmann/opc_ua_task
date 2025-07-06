#include <stdio.h>
#include <stdlib.h>
#include <libpq-fe.h>
#include "open62541.h"
#include <time.h>
#include <string.h>
#include <stdio.h>
#include <windows.h>
#include <time.h>

#define MAX_OBJECTS 100
#define INITIAL_TAG_CAPACITY 10000

typedef enum { TYPE_DOUBLE, TYPE_INT32, TYPE_BOOLEAN, TYPE_BYTESTRING, TYPE_XMLELEMENT } TagType;

typedef struct {
    char name[256];
    TagType type;
    UA_NodeId nodeId;
} Tag;

typedef struct {
    char* table_name;
    UA_NodeId objectNodeId;
    Tag* tags;
    int tagCount;
    int tagCapacity;
} ObjectWithTags;

static ObjectWithTags* objects = NULL;
static int objectCount = 0;
static char **created_array = NULL;
static int created_count = 0;

// Добавляем функцию для проверки существования таблицы в БД
static bool table_exists(PGconn *conn, const char *table_name) { // если не существует таблица то потом ее удаляем через ф-юю ниже
    char query[256];
    snprintf(query, sizeof(query),
             "SELECT 1 FROM information_schema.tables WHERE table_name = '%s'",
             table_name);

    PGresult *res = PQexec(conn, query);
    if (PQresultStatus(res) != PGRES_TUPLES_OK) {
        PQclear(res);
        return false;
    }

    bool exists = (PQntuples(res) > 0);
    PQclear(res);
    return exists;
}

// Функция для удаления объекта и его тэгов
static void removeObject(UA_Server *server, int objectIndex) {
    // Удаляем все теги объекта
    for (int i = 0; i < objects[objectIndex].tagCount; i++) {
        UA_Server_deleteNode(server, objects[objectIndex].tags[i].nodeId, true);
    }

    // Удаляем объект
    UA_Server_deleteNode(server, objects[objectIndex].objectNodeId, true);

    // освобождаем память
    free(objects[objectIndex].table_name);
    free(objects[objectIndex].tags);

    // сдвигаем оставшиеся объекты в массиве
    for (int i = objectIndex; i < objectCount - 1; i++) {
        objects[i] = objects[i + 1];
    }

    objectCount--;
}

// get_device_tables
char **get_device_tables(PGconn *conn, int *count) {
    if (!conn || PQstatus(conn) != CONNECTION_OK) {
        fprintf(stderr, "Неверно подключение к БД\n");
        return NULL;
    }

    const char *query = "SELECT table_name FROM information_schema.tables "
                       "WHERE table_name LIKE 'device_%' AND table_schema = 'public'";
    PGresult *res = PQexec(conn, query);

    if (PQresultStatus(res) != PGRES_TUPLES_OK) {
        fprintf(stderr, "Ошибка запроса: %s\n", PQerrorMessage(conn));
        PQclear(res);
        return NULL;
    }

    *count = PQntuples(res);
    if (*count == 0) {
        PQclear(res);
        return NULL;
    }

    char **tables = malloc(*count * sizeof(char *));
    if (!tables) {
        fprintf(stderr, "Ошибка malloc памяти\n");
        PQclear(res);
        return NULL;
    }

    for (int i = 0; i < *count; i++) {
        tables[i] = strdup(PQgetvalue(res, i, 0));
        if (!tables[i]) {
            fprintf(stderr, "Ошибка выделения памяти для строки\n");
            for (int j = 0; j < i; j++) {
                free(tables[j]);
            }
            free(tables);
            PQclear(res);
            return NULL;
        }
    }

    PQclear(res);
    return tables;
}

static void addVariable(UA_Server *server, UA_NodeId parentNodeId, ObjectWithTags* object,
                       const char *name, const char *tagType, const char *tagValue) {
    if (object->tagCount >= object->tagCapacity) {
        int newCapacity = object->tagCapacity * 2;
        Tag* newTags = realloc(object->tags, newCapacity * sizeof(Tag));
        if (!newTags) {
            fprintf(stderr, "Попытка realloc массив tags - провалилась \n");
            return;
        }
        object->tags = newTags;
        object->tagCapacity = newCapacity;
    }

    TagType type;
    if (strcmp(tagType, "Double") == 0)
        type = TYPE_DOUBLE;
    else if (strcmp(tagType, "Int") == 0 || strcmp(tagType, "Int32") == 0)
        type = TYPE_INT32;
    else if (strcmp(tagType, "Boolean") == 0)
        type = TYPE_BOOLEAN;
    else if (strcmp(tagType, "ByteString") == 0)
        type = TYPE_BYTESTRING;
    else
        type = TYPE_XMLELEMENT;

    UA_VariableAttributes attr = UA_VariableAttributes_default;

    switch(type) {
        case TYPE_DOUBLE: {
            UA_Double val = atof(tagValue);
            UA_Variant_setScalar(&attr.value, &val, &UA_TYPES[UA_TYPES_DOUBLE]);
            break;
        }
        case TYPE_INT32: {
            UA_Int32 val = atoi(tagValue);
            UA_Variant_setScalar(&attr.value, &val, &UA_TYPES[UA_TYPES_INT32]);
            break;
        }
        case TYPE_BOOLEAN: {
            //UA_Boolean val = atob(tagValue);
            UA_Boolean val = (strcmp(tagValue, "True") == 0 || strcmp(tagValue, "1") == 0) ? true : false;
            UA_Variant_setScalar(&attr.value, &val, &UA_TYPES[UA_TYPES_BOOLEAN]);
            break;
        }
        case TYPE_BYTESTRING: {
            UA_ByteString val = UA_BYTESTRING_ALLOC(tagValue);
            UA_Variant_setScalar(&attr.value, &val, &UA_TYPES[UA_TYPES_BYTESTRING]);
            break;
        }
        case TYPE_XMLELEMENT: {
            UA_String val = UA_STRING_ALLOC(tagValue);
            UA_Variant_setScalar(&attr.value, &val, &UA_TYPES[UA_TYPES_XMLELEMENT]);
            break;
        }
    }

    attr.displayName = UA_LOCALIZEDTEXT("en-US", name);
    attr.accessLevel = UA_ACCESSLEVELMASK_READ | UA_ACCESSLEVELMASK_WRITE;

    UA_NodeId varNodeId;
    UA_Server_addVariableNode(
        server, UA_NODEID_NULL, parentNodeId, UA_NODEID_NUMERIC(0, UA_NS0ID_HASCOMPONENT),
        UA_QUALIFIEDNAME(2, name),
        UA_NODEID_NUMERIC(0, UA_NS0ID_BASEDATAVARIABLETYPE), attr, NULL, &varNodeId);

    // cохран тег в массив tags конкретного объекта
    object->tags[object->tagCount].nodeId = varNodeId;
    object->tags[object->tagCount].type = type;
    strncpy(object->tags[object->tagCount].name, name, sizeof(object->tags[object->tagCount].name) - 1);
    object->tagCount++;
}

static void writeVariable(UA_Server *server, ObjectWithTags* object, int tagIndex,
                         const char *tagType, const char *tagValue) {
    TagType type;
    if (strcmp(tagType, "Double") == 0)
        type = TYPE_DOUBLE;
    else if (strcmp(tagType, "Int") == 0 || strcmp(tagType, "Int32") == 0)
        type = TYPE_INT32;
    else if (strcmp(tagType, "Boolean") == 0)
        type = TYPE_BOOLEAN;
    else if (strcmp(tagType, "ByteString") == 0)
        type = TYPE_BYTESTRING;
    else
        type = TYPE_XMLELEMENT;

    switch(type) {
        case TYPE_DOUBLE: {
            UA_Double val = atof(tagValue);
            UA_Variant value;
            UA_Variant_setScalar(&value, &val, &UA_TYPES[UA_TYPES_DOUBLE]);
            UA_Server_writeValue(server, object->tags[tagIndex].nodeId, value);
            break;
        }
        case TYPE_INT32: {
            UA_Int32 val = atoi(tagValue);
            UA_Variant value;

            UA_Variant_setScalar(&value, &val, &UA_TYPES[UA_TYPES_INT32]);
            UA_Server_writeValue(server, object->tags[tagIndex].nodeId, value);
            break;
        }
        case TYPE_BOOLEAN: {
            UA_Boolean val = (strcmp(tagValue, "True") == 0 || strcmp(tagValue, "1") == 0) ? true : false;
            UA_Variant value;

            UA_Variant_setScalar(&value, &val, &UA_TYPES[UA_TYPES_BOOLEAN]);
            UA_Server_writeValue(server, object->tags[tagIndex].nodeId, value);
            break;
        }
        case TYPE_BYTESTRING: { //
            UA_ByteString val = UA_BYTESTRING_ALLOC(tagValue);
            UA_Variant value;

            UA_Variant_setScalar(&value, &val, &UA_TYPES[UA_TYPES_BYTESTRING]);
            UA_Server_writeValue(server, object->tags[tagIndex].nodeId, value);
            UA_ByteString_clear(&val);
            break;
        }
        case TYPE_XMLELEMENT: {
            UA_String val = UA_STRING_ALLOC(tagValue);
            UA_Variant value;

            UA_Variant_setScalar(&value, &val, &UA_TYPES[UA_TYPES_XMLELEMENT]);
            UA_Server_writeValue(server, object->tags[tagIndex].nodeId, value);
            UA_String_clear(&val);
            break;
        }
    }
}

ObjectWithTags* findOrCreateObject(const char* table_name, UA_Server* server, UA_UInt16 nsIndex) {
    // поиск существующего объекта
    for (int i = 0; i < objectCount; i++) {
        if (strcmp(objects[i].table_name, table_name) == 0) {
            return &objects[i];
        }
    }

    // Созд нового объекта
    ObjectWithTags* newObjects = realloc(objects, (objectCount + 1) * sizeof(ObjectWithTags));
    if (!newObjects) {
        fprintf(stderr, "Попытка выделить память под новый object провалилась !\n");
        return NULL;
    }
    objects = newObjects;

    ObjectWithTags* newObj = &objects[objectCount];
    newObj->table_name = strdup(table_name);
    newObj->tagCount = 0;
    newObj->tagCapacity = INITIAL_TAG_CAPACITY;
    newObj->tags = malloc(INITIAL_TAG_CAPACITY * sizeof(Tag));
    if (!newObj->tags) {
        free(newObj->table_name);
        return NULL;
    }

    // Создаем ноду объекта на СИ сервере
    UA_ObjectAttributes oAttr = UA_ObjectAttributes_default;
    oAttr.displayName = UA_LOCALIZEDTEXT("en-US", table_name);

    UA_Server_addObjectNode(
        server, UA_NODEID_NULL, UA_NODEID_NUMERIC(0, UA_NS0ID_OBJECTSFOLDER),
        UA_NODEID_NUMERIC(0, UA_NS0ID_ORGANIZES), UA_QUALIFIEDNAME(nsIndex, table_name),
        UA_NODEID_NUMERIC(0, UA_NS0ID_BASEOBJECTTYPE), oAttr, NULL, &newObj->objectNodeId);

    objectCount++;
    return newObj;
}

// Функция для синхронизации тэгов объекта с таблицей в БД
static void syncObjectTags(UA_Server *server, PGconn *conn, ObjectWithTags* obj) {
    // 1. Берем тэги из БД
    char query[512];
    snprintf(query, sizeof(query),
        "SELECT DISTINCT ON (tag_name) tag_name, tag_type, tag_value "
        "FROM %s ORDER BY tag_name, timestamp DESC",
        obj->table_name);

    PGresult *res = PQexec(conn, query);
    if (PQresultStatus(res) != PGRES_TUPLES_OK) {
        PQclear(res);
        return;
    }

    int db_tag_count = PQntuples(res);

    // 2. Проверяем какие теги нужно удалить (есть на СИ сервере, но нет в БД)
    for (int i = 0; i < obj->tagCount; i++) {
        bool found_in_db = false;

        for (int j = 0; j < db_tag_count; j++) {
            if (strcmp(obj->tags[i].name, PQgetvalue(res, j, 0)) == 0) {
                found_in_db = true;
                break;
            }
        }

        if (!found_in_db) {
            // Тег есть на сервере, но нет в БД - удаляем
            UA_Server_deleteNode(server, obj->tags[i].nodeId, true);

            // Сдвиг
            for (int k = i; k < obj->tagCount - 1; k++) {
                obj->tags[k] = obj->tags[k + 1];
            }

            obj->tagCount--;
            i--; // правильный индекс
        }
    }

    // 3. Добавляем /обновляем существующие теги
    for (int j = 0; j < db_tag_count; j++) {
        const char* tag_name = PQgetvalue(res, j, 0);
        const char* tag_type = PQgetvalue(res, j, 1);
        const char* tag_value = PQgetvalue(res, j, 2);

        bool tag_exists = false;
        for (int i = 0; i < obj->tagCount; i++) {
            if (strcmp(obj->tags[i].name, tag_name) == 0) {
                // Тег существует - обновляем его значение
                writeVariable(server, obj, i, tag_type, tag_value);
                tag_exists = true;
                break;
            }
        }

        if (!tag_exists) {
            // если новый тег - добавляем
            addVariable(server, obj->objectNodeId, obj, tag_name, tag_type, tag_value);
        }
    }

    PQclear(res);
}

int main(int argc, char **argv) {
    UA_Server *server = UA_Server_new();
    UA_ServerConfig_setMinimal(UA_Server_getConfig(server), 4841, NULL);

    const char *uri = "http://examples.freeopcua555555.github.io";
    UA_UInt16 nsIndex = UA_Server_addNamespace(server, uri);

    UA_StatusCode retval = UA_Server_run_startup(server);
    if (retval != UA_STATUSCODE_GOOD) {
        printf("Запуск сервера провалился : %s\n", UA_StatusCode_name(retval));
        return (int)retval;
    }

    const char *conninfo = "host=localhost dbname=opc_ua_task user=postgres password=password"; // info для подключения к БД
    PGconn *conn = PQconnectdb(conninfo);

    while (true) {
        clock_t start = clock(); // начало замера
        int table_cnt = 0;
        char **nameArray = get_device_tables(conn, &table_cnt); // Получаем текущий список таблиц и колво из БД


        // Проверяем какие объекты нужно удалить (таблицы в БД уже нет, а объект остался)
        for (int i = 0; i < objectCount; i++) {
            bool found = false;
            for (int j = 0; j < table_cnt; j++) {
                if (strcmp(objects[i].table_name, nameArray[j]) == 0) {
                    found = true;
                    break;
                }
            }

            if (!found) {
                // Дополнительная проверка через запрк БД
                if (!table_exists(conn, objects[i].table_name)) {
                    printf("Удаляем объект %s\n", objects[i].table_name);
                    removeObject(server, i);
                    i--; // Так как массив сдвинулся
                }
            }
        } // блок для удаления ---- конец

        // блок кода для создания или записи новых значений в тэги объектов.
        // Для каждого существующего объекта синхронизируем теги
        for (int i = 0; i < objectCount; i++) {
            syncObjectTags(server, conn, &objects[i]);
        }
        // Создаем новые объекты для новых таблиц
        for (int i = 0; i < table_cnt; i++) {
            bool exists = false;
            for (int j = 0; j < objectCount; j++) {
                if (strcmp(objects[j].table_name, nameArray[i]) == 0) {
                    exists = true;
                    break;
                }
            }

            if (!exists) {
                ObjectWithTags* obj = findOrCreateObject(nameArray[i], server, nsIndex);
                if (obj) {
                    syncObjectTags(server, conn, obj);
                }
            }
        }

        // Sleep(1000);
        UA_Server_run_iterate(server, false);

        clock_t end = clock(); // Конец замера времени
        double duration = ((double)(end - start)) / CLOCKS_PER_SEC;
        printf("\n Время итерации:  %.5f  сек! \n", duration);
    }

    // Очистка памяти
    for (int i = 0; i < objectCount; i++) {
        free(objects[i].table_name);
        free(objects[i].tags);
    }
    free(objects);
    PQfinish(conn);
    UA_Server_delete(server);
    return 0;
}