find_package(Eigen3)
include_directories(SYSTEM ${EIGEN3_INCLUDE_DIRS})

# module with a pipeline that returns a constant value
ectomodule(pipelines DESTINATION object_recognition_core/ecto_cells
                     INSTALL
                     module.cpp
                     ConstantPipeline.cpp
)

link_ecto(pipelines ${OpenCV_LIBRARIES}
                    object_recognition_core_common
)
