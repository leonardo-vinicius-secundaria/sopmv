cmake_minimum_required(VERSION 3.16)
project(sopmv_cplex LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin")

option(BUILD_TESTING "Build tests" ON)
set(CPLEX_ROOT_DIR "$ENV{CPLEX_ROOT_DIR}" CACHE PATH "IBM ILOG CPLEX Studio installation root")

add_library(sopmv_core
    src/core/instance.cpp
    src/core/solution_validator.cpp
    src/core/sopmv_generator.cpp
)
target_include_directories(sopmv_core PUBLIC "${CMAKE_CURRENT_SOURCE_DIR}/src/core")
target_compile_options(sopmv_core PRIVATE -Wall -Wextra -Wpedantic)

add_executable(generate_sopmv src/generate_main.cpp)
target_link_libraries(generate_sopmv PRIVATE sopmv_core)
target_compile_options(generate_sopmv PRIVATE -Wall -Wextra -Wpedantic)

add_executable(sopmv_sa src/sa_pd/main.cpp src/sa_pd/sa_pd.cpp)
target_link_libraries(sopmv_sa PRIVATE sopmv_core)
target_compile_options(sopmv_sa PRIVATE -Wall -Wextra -Wpedantic)

add_executable(sopmv_greedy src/greedy/main.cpp src/greedy/greedy.cpp)
target_include_directories(sopmv_greedy PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/src/greedy")
target_link_libraries(sopmv_greedy PRIVATE sopmv_core)
target_compile_options(sopmv_greedy PRIVATE -Wall -Wextra -Wpedantic)

add_executable(sopmv_ils src/ils/main.cpp src/ils/ils.cpp src/greedy/greedy.cpp)
target_include_directories(sopmv_ils PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/src/ils" "${CMAKE_CURRENT_SOURCE_DIR}/src/greedy")
target_link_libraries(sopmv_ils PRIVATE sopmv_core)
target_compile_options(sopmv_ils PRIVATE -Wall -Wextra -Wpedantic)

add_executable(sopmv_ils_new_version
    src/ils/main.cpp
    src/ils/ils_new_version.cpp
    src/greedy/greedy.cpp
)
target_include_directories(sopmv_ils_new_version PRIVATE
    "${CMAKE_CURRENT_SOURCE_DIR}/src/ils"
    "${CMAKE_CURRENT_SOURCE_DIR}/src/greedy"
)
target_link_libraries(sopmv_ils_new_version PRIVATE sopmv_core)
target_compile_options(sopmv_ils_new_version PRIVATE -Wall -Wextra -Wpedantic)

# Versao didatica do ILS: mesma logica, mas com rastreamento detalhado no terminal.
add_executable(sopmv_ils_trace src/ils/main.cpp src/ils/ils_trace.cpp src/greedy/greedy.cpp)
target_include_directories(sopmv_ils_trace PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/src/ils" "${CMAKE_CURRENT_SOURCE_DIR}/src/greedy")
target_link_libraries(sopmv_ils_trace PRIVATE sopmv_core)
target_compile_options(sopmv_ils_trace PRIVATE -Wall -Wextra -Wpedantic)

set(CPLEX_FOUND FALSE)
if(CPLEX_ROOT_DIR)
    find_path(CPLEX_INCLUDE_DIR ilcplex/ilocplex.h
        HINTS "${CPLEX_ROOT_DIR}/cplex/include" NO_DEFAULT_PATH)
    find_path(CONCERT_INCLUDE_DIR ilconcert/iloenv.h
        HINTS "${CPLEX_ROOT_DIR}/concert/include" NO_DEFAULT_PATH)
    find_library(CPLEX_LIBRARY NAMES cplex
        HINTS "${CPLEX_ROOT_DIR}/cplex/lib/x86-64_linux/static_pic" NO_DEFAULT_PATH)
    find_library(ILOCPLEX_LIBRARY NAMES ilocplex
        HINTS "${CPLEX_ROOT_DIR}/cplex/lib/x86-64_linux/static_pic" NO_DEFAULT_PATH)
    find_library(CONCERT_LIBRARY NAMES concert
        HINTS "${CPLEX_ROOT_DIR}/concert/lib/x86-64_linux/static_pic" NO_DEFAULT_PATH)
    if(CPLEX_INCLUDE_DIR AND CONCERT_INCLUDE_DIR AND CPLEX_LIBRARY AND
       ILOCPLEX_LIBRARY AND CONCERT_LIBRARY)
        set(CPLEX_FOUND TRUE)
    endif()
endif()

if(CPLEX_FOUND)
    find_package(Threads REQUIRED)
    add_library(sopmv_cplex_model src/cplex/sopmv_model.cpp)
    target_include_directories(sopmv_cplex_model PUBLIC
        "${CMAKE_CURRENT_SOURCE_DIR}/src/core"
        "${CMAKE_CURRENT_SOURCE_DIR}/src/cplex"
        "${CPLEX_INCLUDE_DIR}"
        "${CONCERT_INCLUDE_DIR}"
    )
    target_compile_definitions(sopmv_cplex_model PUBLIC IL_STD)
    target_compile_options(sopmv_cplex_model PRIVATE -Wall -Wextra -Wpedantic)
    target_link_libraries(sopmv_cplex_model PUBLIC sopmv_core
        "${ILOCPLEX_LIBRARY}" "${CPLEX_LIBRARY}" "${CONCERT_LIBRARY}"
        Threads::Threads dl m)

    add_executable(sopmv_cplex src/cplex/main.cpp)
    target_link_libraries(sopmv_cplex PRIVATE sopmv_cplex_model)
    target_compile_options(sopmv_cplex PRIVATE -Wall -Wextra -Wpedantic)

    add_library(sopmv_cplex_branch_cut_model src/cplex/sopmv_model_branch_cut.cpp)
    target_include_directories(sopmv_cplex_branch_cut_model PUBLIC
        "${CMAKE_CURRENT_SOURCE_DIR}/src/core"
        "${CMAKE_CURRENT_SOURCE_DIR}/src/cplex"
        "${CPLEX_INCLUDE_DIR}"
        "${CONCERT_INCLUDE_DIR}"
    )
    target_compile_definitions(sopmv_cplex_branch_cut_model PUBLIC IL_STD)
    target_compile_options(sopmv_cplex_branch_cut_model PRIVATE -Wall -Wextra -Wpedantic)
    target_link_libraries(sopmv_cplex_branch_cut_model PUBLIC sopmv_core
        "${ILOCPLEX_LIBRARY}" "${CPLEX_LIBRARY}" "${CONCERT_LIBRARY}"
        Threads::Threads dl m)

    add_executable(sopmv_cplex_branch_cut src/cplex/main.cpp)
    target_compile_definitions(sopmv_cplex_branch_cut PRIVATE SOPMV_BRANCH_AND_CUT)
    target_link_libraries(sopmv_cplex_branch_cut PRIVATE sopmv_cplex_branch_cut_model)
    target_compile_options(sopmv_cplex_branch_cut PRIVATE -Wall -Wextra -Wpedantic)
    message(STATUS "CPLEX support enabled from ${CPLEX_ROOT_DIR}")
else()
    message(WARNING "CPLEX not found: sopmv_cplex and CPLEX tests will not be built. Set CPLEX_ROOT_DIR.")
endif()

if(BUILD_TESTING)
    enable_testing()
    add_executable(test_parser tests/test_parser.cpp)
    target_link_libraries(test_parser PRIVATE sopmv_core)
    target_compile_definitions(test_parser PRIVATE TEST_SOURCE_DIR="${CMAKE_CURRENT_SOURCE_DIR}")
    add_test(NAME parser COMMAND test_parser)

    add_executable(test_small_instance tests/test_small_instance.cpp)
    target_link_libraries(test_small_instance PRIVATE sopmv_core)
    target_compile_definitions(test_small_instance PRIVATE TEST_SOURCE_DIR="${CMAKE_CURRENT_SOURCE_DIR}")
    add_test(NAME small_validator COMMAND test_small_instance)

    add_executable(test_greedy tests/test_greedy.cpp src/greedy/greedy.cpp)
    target_include_directories(test_greedy PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/src/greedy")
    target_link_libraries(test_greedy PRIVATE sopmv_core)
    target_compile_definitions(test_greedy PRIVATE TEST_SOURCE_DIR="${CMAKE_CURRENT_SOURCE_DIR}")
    add_test(NAME greedy COMMAND test_greedy)

    add_executable(test_ils tests/test_ils.cpp src/ils/ils.cpp src/greedy/greedy.cpp)
    target_include_directories(test_ils PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/src/ils" "${CMAKE_CURRENT_SOURCE_DIR}/src/greedy")
    target_link_libraries(test_ils PRIVATE sopmv_core)
    target_compile_definitions(test_ils PRIVATE TEST_SOURCE_DIR="${CMAKE_CURRENT_SOURCE_DIR}")
    add_test(NAME ils COMMAND test_ils)

    add_executable(test_ils_acceptance
        tests/test_ils_acceptance.cpp
        src/ils/ils_new_version.cpp
        src/greedy/greedy.cpp
    )
    target_include_directories(test_ils_acceptance PRIVATE
        "${CMAKE_CURRENT_SOURCE_DIR}/src/ils"
        "${CMAKE_CURRENT_SOURCE_DIR}/src/greedy"
    )
    target_link_libraries(test_ils_acceptance PRIVATE sopmv_core)
    target_compile_definitions(test_ils_acceptance PRIVATE
        TEST_SOURCE_DIR="${CMAKE_CURRENT_SOURCE_DIR}"
    )
    add_test(NAME ils_acceptance COMMAND test_ils_acceptance)

    if(CPLEX_FOUND)
        add_executable(test_cplex_small tests/test_cplex_small.cpp)
        target_link_libraries(test_cplex_small PRIVATE sopmv_cplex_model)
        target_compile_definitions(test_cplex_small PRIVATE TEST_SOURCE_DIR="${CMAKE_CURRENT_SOURCE_DIR}")
        add_test(NAME cplex_small COMMAND test_cplex_small)

        add_executable(test_cplex_berlin tests/test_cplex_berlin.cpp)
        target_link_libraries(test_cplex_berlin PRIVATE sopmv_cplex_model)
        target_compile_definitions(test_cplex_berlin PRIVATE TEST_SOURCE_DIR="${CMAKE_CURRENT_SOURCE_DIR}")
        add_test(NAME cplex_berlin COMMAND test_cplex_berlin)
        set_tests_properties(cplex_berlin PROPERTIES TIMEOUT 660)

        add_executable(test_cplex_branch_cut tests/test_cplex_branch_cut.cpp)
        target_link_libraries(test_cplex_branch_cut PRIVATE sopmv_cplex_branch_cut_model)
        target_compile_definitions(test_cplex_branch_cut PRIVATE TEST_SOURCE_DIR="${CMAKE_CURRENT_SOURCE_DIR}")
        add_test(NAME cplex_branch_cut COMMAND test_cplex_branch_cut)
    endif()
endif()
