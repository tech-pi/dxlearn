import dxl.learn.dataset as dld
import unittest




class TestPartition(unittest.TestCase):
    DATASET_SIZE = 100
    TRAIN_DATASET_SIZE = 80

    def train_ids(self):
        return list(range(self.TRAIN_DATASET_SIZE))

    def test_ids(self):
        return list(range(self.TRAIN_DATASET_SIZE, self.DATASET_SIZE))

    def create_partition(self):
        return dld.Partition({
            dld.Partition.KEYS.TRAIN: self.train_ids(),
            dld.Partition.KEYS.TEST: self.test_ids()
        })

    def sample_at_least_one_epoch(self, key):
        samples = []
        for _ in range(self.DATASET_SIZE):
            samples.append(next(p[key]))
        return samples

    def test_train_ids(self):
        p = self.create_partition()
        samples = self.sample_at_least_one_epoch(dld.Partition.KEYS.TRAIN)
        assert set(samples) == set(self.train_ids())

    def test_test_ids(self):
        p = self.create_partition()
        samples = self.sample_at_least_one_epoch(dld.Partition.KEYS.TEST)
        assert set(samples) == set(self.test_ids())


class TestTrain80Partition(unittest.TestCase):
    def create_dataset(self, dataset_size=100, batch_size=32):
        spec = {
            'batch_size': batch_size,
            'dataset_size': dataset_size,
        }
        return dld.Train80Partition(**spec)

    def assertAllSamplesIndexIn(self, samples, target_range):
        self.assertTrue(all(s in target_range for s in samples))

    def assertAllIndexInSamples(self, target_range, samples):
        self.assertTrue(all(s in samples for s in target_range))

    def sample_at_least_one_epoch(self, partition):
        samples = []
        while len(samples) < partition.partition_size():
            samples.append(next(p))
        return samples

    def test_ids(self):
        dataset_size = 100
        partition_size = 80
        p = self.create_dataset(dataset_size)
        samples = self.sample_at_least_one_epoch(p)
        expected = list(range(partition_size))
        self.assertAllSamplesIndexIn(samples, expected)
        self.assertAllIndexInSamples(expected, samples)
