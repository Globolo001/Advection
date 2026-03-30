import numpy as np


class DataParticle():
    def __init__(self, position=(0,0,0), color=None):
        self.position = position
        self.color = color


class DataParticlesCloud:
    def __init__(self, DataParticlesList, min_pos, max_pos):
        self.DataParticlesList = DataParticlesList
        self.count = len(DataParticlesList)
        self.particle_positions = np.array([particle.position for particle in self.DataParticlesList], dtype=np.float64)
        self.min_pos = min_pos
        self.max_pos = max_pos
        self.center = np.mean([self.min_pos, self.max_pos], axis=0)
        self.size = np.subtract(self.max_pos, self.min_pos)


def downsample_particles(cloud, target_count):
    """Downsample a DataParticlesCloud using voxel grid spatial sampling.

    Divides space into a uniform 3D grid and keeps one representative
    particle per occupied cell (the one closest to the cell center).
    This guarantees even spatial coverage — no gaps on flat surfaces.

    Uses iterative binary search on voxel size to converge on the
    target particle count.

    Returns a new DataParticlesCloud with reduced particles.
    """
    if cloud.count <= target_count:
        return cloud

    particles = cloud.DataParticlesList
    positions = cloud.particle_positions  # (N, 3 or 4)

    xyz = positions[:, :3]
    min_xyz = xyz.min(axis=0)
    max_xyz = xyz.max(axis=0)
    extent = max_xyz - min_xyz
    volume = max(np.prod(extent), 1e-12)

    def _count_occupied(vs):
        """Fast occupied-cell count using encoded integer keys."""
        g = ((xyz - min_xyz) / vs).astype(np.int64)
        # Encode 3 ints into 1 for fast unique counting
        mx = int(g[:, 1].max()) + 1
        mz = int(g[:, 2].max()) + 1
        encoded = g[:, 0] * (mx * mz) + g[:, 1] * mz + g[:, 2]
        return len(np.unique(encoded))

    # Initial voxel size estimate
    voxel_size = (volume / target_count) ** (1.0 / 3.0)

    # Binary search for voxel_size that gives ~target_count occupied cells
    lo, hi = voxel_size * 0.001, voxel_size * 1000.0
    best_size = voxel_size
    best_diff = float('inf')
    for _ in range(40):
        mid = (lo + hi) / 2.0
        occupied = _count_occupied(mid)
        diff = abs(occupied - target_count)
        if diff < best_diff:
            best_diff = diff
            best_size = mid
        if occupied > target_count:
            lo = mid
        else:
            hi = mid
        if diff / max(target_count, 1) < 0.05:
            break

    # Use the best voxel size found
    voxel_size = best_size
    grid_indices = ((xyz - min_xyz) / voxel_size).astype(np.int64)

    # For each occupied cell, pick the particle closest to the cell center
    mx = int(grid_indices[:, 1].max()) + 1
    mz = int(grid_indices[:, 2].max()) + 1
    encoded = grid_indices[:, 0] * (mx * mz) + grid_indices[:, 1] * mz + grid_indices[:, 2]

    # Group by encoded cell key using argsort
    order = np.argsort(encoded)
    sorted_enc = encoded[order]
    split_points = np.where(np.diff(sorted_enc) != 0)[0] + 1
    groups = np.split(order, split_points)

    keep_indices = []
    for group in groups:
        if len(group) == 1:
            keep_indices.append(int(group[0]))
        else:
            idx0 = int(group[0])
            key = grid_indices[idx0]
            cell_center = min_xyz + (key.astype(np.float64) + 0.5) * voxel_size
            dists = np.sum((xyz[group] - cell_center) ** 2, axis=1)
            keep_indices.append(int(group[np.argmin(dists)]))

    keep_indices.sort()
    new_particles = [particles[i] for i in keep_indices]

    new_xyz = xyz[keep_indices]
    new_min = tuple(new_xyz.min(axis=0))
    new_max = tuple(new_xyz.max(axis=0))

    print(f"Downsampled {cloud.count} -> {len(new_particles)} particles (voxel grid)")
    return DataParticlesCloud(new_particles, new_min, new_max)