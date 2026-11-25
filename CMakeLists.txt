cmake_minimum_required(VERSION 3.18)

project(rootpart VERSION 0.1.0 LANGUAGES CXX)

include(CMakePackageConfigHelpers)
include(GNUInstallDirs)
find_package(OpenMP)
find_package(Boost REQUIRED)

add_library(rootpart STATIC
    rootpart/src/problem.cpp
    rootpart/src/rpr.cpp
)
add_library(rootpart::rootpart ALIAS rootpart)
target_compile_features(rootpart PUBLIC cxx_std_20)
target_include_directories(rootpart
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/rootpart/include>
        $<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}>
)
target_include_directories(rootpart PRIVATE ${Boost_INCLUDE_DIRS})
set_target_properties(rootpart PROPERTIES POSITION_INDEPENDENT_CODE ON)
if(OpenMP_CXX_FOUND)
    target_link_libraries(rootpart PUBLIC OpenMP::OpenMP_CXX)
endif()

install(
    TARGETS rootpart
    EXPORT rootpartTargets
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
    INCLUDES DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}
)
install(
    DIRECTORY rootpart/include/rootpart
    DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}
)

configure_package_config_file(
    cmake/rootpartConfig.cmake.in
    ${CMAKE_CURRENT_BINARY_DIR}/rootpartConfig.cmake
    INSTALL_DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/rootpart
)
write_basic_package_version_file(
    ${CMAKE_CURRENT_BINARY_DIR}/rootpartConfigVersion.cmake
    VERSION ${PROJECT_VERSION}
    COMPATIBILITY SameMajorVersion
)
install(
    EXPORT rootpartTargets
    FILE rootpartTargets.cmake
    NAMESPACE rootpart::
    DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/rootpart
)
install(
    FILES
        ${CMAKE_CURRENT_BINARY_DIR}/rootpartConfig.cmake
        ${CMAKE_CURRENT_BINARY_DIR}/rootpartConfigVersion.cmake
    DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/rootpart
)
