from types import SimpleNamespace
import transforms3d
import math
import numpy as np
import copy
import cozmo
import itertools

LIGHT_CUBE_LENGTH = 43

# test if objs from buff and navmap are equal disregarding small changes in vision
def blocks_equal(obj1, obj2):
    epsilon_position = 1
    epsilon_rotation = .2
    pos1 = obj1.pose.position
    pos2 = obj2.pose.position
    rot1 = obj1.pose.rotation
    rot2 = obj2.pose.rotation
    pos_a = [pos1.x, pos1.y, pos1.z]
    pos_b = [pos2.x, pos2.y, pos2.z]
    rot_a = [rot1.q0, rot1.q1, rot1.q2, rot1.q3]
    rot_b = [rot2.q0, rot2.q1, rot2.q2, rot2.q3]

    # conditions for equality
    cond_id = obj1.object_id == obj2.object_id
    cond_visible = obj1.is_visible == obj2.is_visible
    cond_pos = abs(max([ai - bi for ai, bi in zip(pos_a, pos_b)])) < epsilon_position
    cond_rot = abs(max([ai - bi for ai, bi in zip(rot_a, rot_b)])) < epsilon_rotation
    return cond_id and cond_visible and cond_pos and cond_rot
    
def block_init(val):
    """
    we only want to send information on blocks whose locations we know.  
    in navmap, it initializes blocks at position (0, 0, 0) even if it cannot see them
    this function checks to see if this is the 'init_block' state
    """
    pos = val.pose.position
    return val.is_visible is False and pos.x == 0.00 and pos.y == 0.00 and pos.z == 0.00

# deepcopy val from navmap
def deepcopy(val):
    d = {}
    n = SimpleNamespace(**d)
    n.object_id = val.object_id
    n.is_visible = val.is_visible
    n.pose = val.pose
    return n

def quaternion_to_euler(quat):
    """
    credit: https://stackoverflow.com/questions/53033620/how-to-convert-euler-angles-to-quaternions-and-get-the-same-euler-angles-back-fr?rq=1
    """
    import math
    (w, x, y, z) = quat
    t0 = +2.0 * (w * x + y * z)
    t1 = +1.0 - 2.0 * (x * x + y * y)
    X = math.atan2(t0, t1)

    t2 = +2.0 * (w * y - z * x)
    t2 = +1.0 if t2 > +1.0 else t2
    t2 = -1.0 if t2 < -1.0 else t2
    Y = math.asin(t2)

    t3 = +2.0 * (w * z + x * y)
    t4 = +1.0 - 2.0 * (y * y + z * z)
    Z = math.atan2(t3, t4)
    return (X, Y, Z)
    
def get_obj_str(obj, str_type):
    position = obj.pose.position
    rotation = obj.pose.rotation
    pos_arr = [position.x, position.y, position.z]
    quat = (rotation.q0, rotation.q1, rotation.q2, rotation.q3)
    oid = obj.object_id

    eul = quaternion_to_euler(quat)

    if isinstance(obj, cozmo.objects.LightCube):
        depth = LIGHT_CUBE_LENGTH
        width = LIGHT_CUBE_LENGTH
        height = LIGHT_CUBE_LENGTH
    
    else:
        depth = obj.x_size_mm
        width = obj.y_size_mm
        height = obj.z_size_mm

    # vectors from center of object to vertices, unrotated
    raw_vectors = itertools.product((depth/2.0, -depth/2.0), (width/2.0, -width/2.0), (height/2.0, -height/2.0))
    vectors = np.transpose(np.array([elt for elt in raw_vectors]))
    rotation_matrix = transforms3d.euler.euler2mat(eul[0], eul[1], eul[2], axes='sxyz')
    rotated_vectors = np.transpose(np.matmul(rotation_matrix, vectors))
    
    # rotated vertices = position array + rotated vectors
    vertices = np.transpose(np.array([[ai + bi for ai, bi in zip(pos_arr, vector)] for vector in rotated_vectors]))
    
    # generate [TRANSFORM] portion of svs string
    scalar = 1000.0   # turns navmap oordinates in mm to SVS coordinates in m
    geo_str = "v"
    for vertex in vertices:
        geo_str += f' {vertex[0]/scalar} {vertex[1]/scalar} {vertex[2]/scalar}'
    svs_str = f"{geo_str} p {pos_arr[0]/scalar} {pos_arr[1]/scalar} {pos_arr[2]/scalar} r {eul[0]} {eul[1]} {eul[2]}"
    
    if str_type == 'add':
        return f'add {oid} world {svs_str}'
    else:
        return f'change {oid} {svs_str}'
