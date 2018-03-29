import numpy as np
from typing import Iterable
from dxl.shape.rotation.matrix import *
from dxl.shape.utils.vector import Vector3
from dxl.shape.utils.axes import Axis3, AXIS3_X, AXIS3_Z

from computeMap import computeMap, siddonMap

from dxl.learn.preprocess import preprocess

import time

import itertools
class Vec3():
    def __init__(self, x=0, y=0, z=0):
        self._x = x
        self._y = y
        self._z = z
    @property
    def x(self):
        return self._x

    @property
    def y(self):
        return self._y

    @property
    def z(self):
        return self._z

    @property
    def value(self):
        return np.array([self.x, self.y, self.z])


class Block():
    def __init__(self, block_size: Vec3, center: Vec3, grid: Vec3, rad_z: np.float32):
        self._block_size = block_size
        self._center = center
        self._grid = grid
        self._rad_z = rad_z

    @property
    def grid(self):
        return self._grid
    @property
    def center(self):
        return self._center
    @property
    def rad_z(self):
        return self._rad_z
    @property
    def block_size(self):
        return self._block_size

    def meshes(self) ->np.array:
        """
        return all of the crystal centers in a block
        """
        bottom_p = -self.block_size.value/2 + self.center.value
        mesh_size = self._block_size.value/self.grid.value
        meshes = np.zeros([self.grid.z, self.grid.y, self.grid.x, 3])
        grid = self.grid
        # print(bottom_p)
        # print()

        for ix in range(grid.x):
            meshes[:, :, ix, 0] = (ix+0.5)*mesh_size[0] + bottom_p[0]
        for iy in range(grid.y):
            meshes[:, iy, :, 1] = (iy+0.5)*mesh_size[1] + bottom_p[1]
        for iz in range(grid.z):
            meshes[iz, :, :, 2] = (iz+0.5)*mesh_size[2] + bottom_p[2]
        # print(meshes.shape)
        meshes = np.transpose(meshes)
        source_axis = AXIS3_X
        target_axis = Axis3(Vector3([np.cos(self.rad_z), np.sin(self.rad_z), 0]))
        rot = axis_to_axis(source_axis, target_axis)
        
        rps = rot@np.reshape(meshes, (3, -1))
        return np.transpose(rps)

        


class RingPET():
    def __init__(self, inner_radius: np.float32, outer_radius: np.float32, gap: np.float32,
                 num_rings: np.int32, num_blocks: np.int32, block_size: Vec3, grid: Vec3):
        self._inner_radius = inner_radius
        self._outer_radius = outer_radius
        self._num_rings = num_rings
        self._num_blocks = num_blocks
        self._block_size = block_size
        self._grid = grid
        self._gap = gap
        # self._block_list: Iterable[Block] = self._make_blocks()
        self._rings = self._make_rings()
    @property
    def inner_radius(self):
        return self._inner_radius

    @property
    def outer_radius(self):
        return self._outer_radius

    @property
    def num_blocks(self):
        return self._num_blocks

    @property
    def num_rings(self):
        return self._num_rings

    @property
    def block_size(self):
        return self._block_size

    @property
    def grid(self):
        return self._grid

    @property
    def gap(self):
        return self._gap
    
    # @property
    # def block_list(self):
    #     return self._block_list
    
    # @property
    def rings(self, num: np.int32):
        """
        obtain a block list of a single ring 
        0: the bottom one
        num_rings - 1: the top one 
        """
        return self._rings[num]

    def _make_rings(self):
        num_rings = self.num_rings
        num_blocks = self.num_blocks
        block_size = self.block_size
        grid = self.grid
        gap = self.gap
        ri = self.inner_radius
        ro = self.outer_radius

        rings = []
        bottom_z = -(block_size.z + gap)*(num_rings-1)/2
        block_x_offset = (ri + ro)/2
        for ir in range(num_rings):
            block_z_offset = bottom_z + ir*(block_size.z + gap)
            pos = Vec3(block_x_offset, 0, block_z_offset)
            # print(num_blocks)
            block_list: Iterable[Block] = []
            for ib in range(num_blocks):
                phi = 360.0/num_blocks*ib
                rad_z = phi/180*np.pi
                block_list.append(Block(block_size, pos, grid, rad_z))
            rings.append(block_list)
        # print(len(rings))
        return rings
    
    # def _make_blocks(self):
    #     num_rings = self.num_rings
    #     num_blocks = self.num_blocks
    #     block_size = self.block_size
    #     grid = self.grid
    #     gap = self.gap
    #     ri = self.inner_radius
    #     ro = self.outer_radius
    #     block_list: Iterable[Block] = []
    #     bottom_z = -(block_size.z + gap)*(num_rings-1)/2
    #     block_x_offset = (ri + ro)/2
    #     for ir in range(num_rings):
    #         block_z_offset = bottom_z + ir*(block_size.z + gap)
    #         pos = Vec3(block_x_offset, 0, block_z_offset)
    #         for ib in range(num_blocks):
    #             phi = 360.0/num_blocks*ib
    #             rad_z = phi/180*np.pi
    #             block_list.append(Block(block_size, pos, grid, rad_z))
    #     return block_list
# class BlockList():


def print_block_pair(bps):
    def pb(b):
        return "({},{})".format(b.center.x, b.center.y)
    return "<{}|{}>".format(pb(bps[0]), pb(bps[1]))

def make_block_pairs(block_list):
    """
    return the block pairs in a block list.
    """
    block_pairs = []
    if len(block_list) == 1:
        # print("1")
        ring = block_list[0]
        # print('len ring:', len(ring))
        
        block_pairs = [[b1, b2] for i1, b1 in enumerate(ring) for i2, b2 in enumerate(ring) if i1 < i2]
        # print('len bps:', len(block_pairs))
        # msg = [print_block_pair(bps) for bps in block_pairs]
        # for bps in block_pairs:
            # print(bps)
        # print('\n'.join(msg))
    else:
        # print("2")
        ring1 = block_list[0]
        ring2 = block_list[1]
        block_pairs = [[b1, b2] for b1 in ring1 for b2 in ring2]
    # print(block_pairs)
    return block_pairs

def make_lors(block_pairs):
    lors = []
    # print((block_pairs))
    for ibp in block_pairs:
        b0 = ibp[0]
        b1 = ibp[1]
        m0 = b0.meshes()
        m1 = b1.meshes()
        lors.append(list(itertools.product(m0, m1)))
    return np.array(lors).reshape(-1, 6)

if __name__ == '__main__':
    # rpet = RingPET(400.0, 420.0, 0.0, 432, 4, Vec3(20, 122.4, 3.4), Vec3(1, 4, 1))
    rpet = RingPET(400.0, 400.0, 0.0, 400, 4, Vec3(20, 160, 4), Vec3(1, 1, 1))
    r1 = rpet.rings(num = 215)
    r2 = rpet.rings(num = 216+50)
    # print(len(r1))
    # print(r2)
    bs = make_block_pairs([r1,])
    # print(len(bs))
    lors = make_lors(bs)
    # print(lors)
    # np.save('./debug/lors.npy', lors[:1000, :])
    print(len(lors))
    # exit()
    xlors, ylors, zlors = preprocess(lors) 
    # np.save('./debug/xlors.npy', xlors[:1000, :])
    # np.save('./debug/ylors.npy', ylors[:1000, :])
    # np.save('./debug/zlors.npy', zlors[:1000, :])
    xlors = xlors[:, [1, 2, 0, 4, 5, 3]] # y z x
    ylors = ylors[:, [0, 2, 1, 3, 5, 4]] # x z y
    # exit()
    grid = [160, 240, 320]
    center = [0., 0., 0.]
    # size = [544.*2., 544.*3., 544.*4.]
    size = [1120., 1680., 2240.]
    origin = [-544., -840., -1120.]
    volsize = [7., 7., 7.] 
    st = time.time()
    # print(xlors.shape)
    # print(ylors.shape)
    slors = np.hstack((lors, np.zeros((lors.shape[0], 1))))
    print(slors.shape)
    # exit()
    effmap = siddonMap(grid, volsize, origin, slors)
    # effmap = computeMap(grid, center, size, xlors, ylors, zlors)
    np.save('./debug/effmap_{}.npy'.format(0), effmap)
    et = time.time()
    tdiff = et-st
    print(effmap)
    print("the total time: {} seconds".format(tdiff))
