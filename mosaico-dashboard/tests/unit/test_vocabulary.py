from mosaico_dashboard.domain.vocabulary import CAMERA, MOTION, OTHER, sensor_type


def test_known_tag_gets_label_and_category():
    imu = sensor_type("IMU")

    assert imu.label == "Motion sensor (IMU)"
    assert imu.category == MOTION


def test_compressed_image_is_a_camera():
    assert sensor_type("CompressedImage").category == CAMERA


def test_unknown_tag_keeps_its_name():
    custom = sensor_type("EncoderTicks")

    assert custom.label == "EncoderTicks"
    assert custom.category == OTHER
