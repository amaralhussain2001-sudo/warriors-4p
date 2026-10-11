# w4p-net: connection helper for warriors-4p (design: docs/research/m5_connection_design.md, option S).
# Build: powershell -File net\w4p-net\build.ps1   (CMake + Ninja + MSVC from Visual Studio Build Tools)
cmake_minimum_required(VERSION 3.16)
project(w4p-net VERSION 0.1.0 LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# libjuice v1.7.4, unmodified (third_party/libjuice). Options as planned in the design note section 3.3.
set(NO_TESTS ON CACHE BOOL "libjuice: no tests" FORCE)
set(NO_SERVER ON CACHE BOOL "libjuice: no STUN/TURN server" FORCE)
set(BUILD_SHARED_LIBS OFF CACHE BOOL "static libraries" FORCE)
add_subdirectory(third_party/libjuice EXCLUDE_FROM_ALL)

add_library(w4pcore STATIC src/codec.cpp src/siphash.cpp)
target_include_directories(w4pcore PUBLIC src)

add_executable(w4p-net src/main.cpp src/helper.cpp src/log.cpp)
target_link_libraries(w4p-net PRIVATE w4pcore LibJuice::LibJuiceStatic)

add_executable(w4p-net-codec-test tests/codec_test.cpp)
target_link_libraries(w4p-net-codec-test PRIVATE w4pcore)

if(WIN32)
	foreach(t w4pcore w4p-net w4p-net-codec-test)
		target_compile_definitions(${t} PRIVATE _WIN32_WINNT=0x0A00 WIN32_LEAN_AND_MEAN NOMINMAX _CRT_SECURE_NO_WARNINGS)
	endforeach()
	target_link_libraries(w4pcore PUBLIC ws2_32)
	target_link_libraries(w4p-net PRIVATE ws2_32 bcrypt winmm)
endif()
if(MSVC)
	foreach(t w4pcore w4p-net w4p-net-codec-test)
		target_compile_options(${t} PRIVATE /W4 /utf-8)
	endforeach()
endif()
