import argparse
import datetime
import multiprocessing
import linecache
import copy
import sys
import threading
import traceback
from time import sleep

from numpy import array
from numpy.linalg import norm

OBJ_PATH = None


def handle_qnan(vector_groups, vector_group_with_qnan, return_dict):
    try:
        qnan_line = vector_group_with_qnan["qnan_line"]
        qnan_index = vector_group_with_qnan["qnan"]
        qnan_vectors = vector_group_with_qnan["vectors"]
        qnan_vector = qnan_vectors[qnan_index]
        qnan_v = qnan_vector["v"]
        this_vector = array([float(x) for x in qnan_v.replace("v ", "").split(" ")])

        satisfied = False
        distance_dict = {}
        vector_dict = {}

        for f_id, vector_group in vector_groups.items():
            for vector_index, vector in enumerate(vector_group["vectors"]):
                if "#QNAN" not in vector["vt"]:
                    a = this_vector
                    b = array([float(x) for x in vector["v"].replace("v ", "").split(" ")])
                    distance = norm(a - b)
                    distance_dict["{}_{}".format(f_id, vector_index)] = distance
                    vector_dict["{}_{}".format(f_id, vector_index)] = vector
        distance_dict = {k: v for k, v in sorted(distance_dict.items(), key=lambda item: item[1])}

        satisfied_threshold = 0.25

        distance_vector_iterator = iter(distance_dict)
        while not satisfied:

            qnan_vectors_c = copy.deepcopy(qnan_vectors)
            del qnan_vectors_c[qnan_index]

            closest_vector_key = next(distance_vector_iterator, None)
            if closest_vector_key is None:
                satisfied_threshold += 0.05
                distance_vector_iterator = iter(distance_dict)
            else:
                satisfied = True

                closest_vector = vector_dict[closest_vector_key]
                this_vector_vt = closest_vector["vt"]
                this_vt_numpy = array([float(x) for x in this_vector_vt.replace("vt ", "").split(" ")])

                for qnan_vector_sibling in qnan_vectors_c:
                    sibling_vector_vt = qnan_vector_sibling["vt"]
                    sibling_vt_numpy = array([float(x) for x in sibling_vector_vt.replace("vt ", "").split(" ")])
                    vt_distance = norm(this_vt_numpy - sibling_vt_numpy)
                    if vt_distance > satisfied_threshold:
                        # print("Not satisfied with vt_distance of {}, v dist: {}".format(vt_distance, distance_dict[closest_vector_key]))
                        satisfied = False
                        # if attempts >= 10:
                        #     print("Too many attempts, giving up")
                        #     satisfied = True
                        # else:
                        #     attempts += 1
                        break

        print("Repaired with vt dist: {}, v dist: {}".format(vt_distance, str(distance_dict[closest_vector_key])))
        return_dict[qnan_line] = closest_vector["vt"]
    except Exception:
        print(traceback.format_exc())


def main():
    vector_groups = {}
    qnan_groups = {}

    with open(OBJ_PATH, "r") as obj_file:

        for i, line in enumerate(obj_file, start=1):
            line = line.strip()
            if line.startswith("f "):

                vectors = []

                if linecache.getline(OBJ_PATH, i - 9).startswith("v ") and linecache.getline(OBJ_PATH,
                                                                                             i - 7).startswith("vt "):
                    vectors.append({"v": linecache.getline(OBJ_PATH, i - 9), "vt": linecache.getline(OBJ_PATH, i - 7)})
                if linecache.getline(OBJ_PATH, i - 6).startswith("v ") and linecache.getline(OBJ_PATH,
                                                                                             i - 4).startswith("vt "):
                    vectors.append({"v": linecache.getline(OBJ_PATH, i - 6), "vt": linecache.getline(OBJ_PATH, i - 4)})
                if linecache.getline(OBJ_PATH, i - 3).startswith("v ") and linecache.getline(OBJ_PATH,
                                                                                             i - 1).startswith("vt "):
                    vectors.append({"v": linecache.getline(OBJ_PATH, i - 3), "vt": linecache.getline(OBJ_PATH, i - 1)})

                vector_group_object = {
                    "i": i,
                    "vectors": vectors
                }

                if "#QNAN" in linecache.getline(OBJ_PATH, i - 7):
                    qnan_groups[i - 7] = i
                    vector_group_object["qnan"] = 0
                    vector_group_object["qnan_line"] = i - 7
                if "#QNAN" in linecache.getline(OBJ_PATH, i - 4):
                    qnan_groups[i - 4] = i
                    vector_group_object["qnan"] = 1
                    vector_group_object["qnan_line"] = i - 4
                if "#QNAN" in linecache.getline(OBJ_PATH, i - 1):
                    qnan_groups[i - 1] = i
                    vector_group_object["qnan"] = 2
                    vector_group_object["qnan_line"] = i - 1
                vector_groups[i] = vector_group_object

    print("{} qnans to repair...".format(len(qnan_groups)))

    manager = multiprocessing.Manager()
    repaired_qnans = manager.dict()
    all_processes = []
    for i in qnan_groups.keys():
        p = multiprocessing.Process(target=handle_qnan,
                                    args=(vector_groups, vector_groups[qnan_groups[i]], repaired_qnans))
        all_processes.append(p)

    for p in all_processes:
        p.start()

    for p in all_processes:
        p.join()

    print("It looks like all threads are done.")
    print(len(repaired_qnans))
    print(repaired_qnans)

    with open(OBJ_PATH, "r") as obj_file:

        output_file = open("repaired.obj", "w")

        for i, line in enumerate(obj_file, start=1):

            line = line.strip()

            if i in repaired_qnans.keys():
                line_to_write = repaired_qnans[i]
            else:
                line_to_write = line

            output_file.write(line_to_write)
            output_file.write("\n")

        output_file.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--file', help='The OBJ file to repair')
    args = parser.parse_args()
    OBJ_PATH = args.file
    print('Starting up @ {}'.format(datetime.datetime.now()))
    main()
