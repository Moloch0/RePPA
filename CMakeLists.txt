cmake_minimum_required(VERSION 3.18)

project(RePPA VERSION 0.2.0 LANGUAGES CXX)

include(CMakePackageConfigHelpers)
include(GNUInstallDirs)
find_package(OpenMP)
find_package(Boost REQUIRED)

add_library(RePPA STATIC
    reppa/src/problem.cpp
    reppa/src/rpr.cpp
)
add_library(RePPA::RePPA ALIAS RePPA)
target_compile_features(RePPA PUBLIC cxx_std_20)
target_include_directories(RePPA
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/reppa/include>
        $<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}>
)
target_include_directories(RePPA PRIVATE ${Boost_INCLUDE_DIRS})
set_target_properties(RePPA PROPERTIES POSITION_INDEPENDENT_CODE ON)
if(OpenMP_CXX_FOUND)
    target_link_libraries(RePPA PUBLIC OpenMP::OpenMP_CXX)
endif()

install(
    TARGETS RePPA
    EXPORT RePPATargets
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
    INCLUDES DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}
)
install(
    DIRECTORY reppa/include/reppa
    DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}
)

configure_package_config_file(
    cmake/RePPAConfig.cmake.in
    ${CMAKE_CURRENT_BINARY_DIR}/RePPAConfig.cmake
    INSTALL_DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/RePPA
)
write_basic_package_version_file(
    ${CMAKE_CURRENT_BINARY_DIR}/RePPAConfigVersion.cmake
    VERSION ${PROJECT_VERSION}
    COMPATIBILITY SameMajorVersion
)
install(
    EXPORT RePPATargets
    FILE RePPATargets.cmake
    NAMESPACE RePPA::
    DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/RePPA
)
install(
    FILES
        ${CMAKE_CURRENT_BINARY_DIR}/RePPAConfig.cmake
        ${CMAKE_CURRENT_BINARY_DIR}/RePPAConfigVersion.cmake
    DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/RePPA
)
