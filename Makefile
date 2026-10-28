CXX ?= g++
CXXFLAGS ?= -O2 -g
CPPFLAGS += -Isrc/core
WARNINGS := -Wall -Wextra -Wpedantic
STD := -std=c++17

BIN_DIR := build/bin
BUILD_DIR := build
CORE_SOURCES := src/core/instance.cpp src/core/solution_validator.cpp src/core/sopmv_generator.cpp
TEST_DEFINE := -DTEST_SOURCE_DIR=\"$(CURDIR)\"

CPLEX_ARCH ?= x86-64_linux
CPLEX_INCLUDE := $(CPLEX_ROOT_DIR)/cplex/include
CONCERT_INCLUDE := $(CPLEX_ROOT_DIR)/concert/include
CPLEX_LIB_DIR := $(CPLEX_ROOT_DIR)/cplex/lib/$(CPLEX_ARCH)/static_pic
CONCERT_LIB_DIR := $(CPLEX_ROOT_DIR)/concert/lib/$(CPLEX_ARCH)/static_pic
CPLEX_CPPFLAGS := -DIL_STD -Isrc/cplex -I$(CPLEX_INCLUDE) -I$(CONCERT_INCLUDE)
CPLEX_LDLIBS := -L$(CPLEX_LIB_DIR) -lilocplex -lcplex \
	-L$(CONCERT_LIB_DIR) -lconcert -lpthread -ldl -lm

CORE_TARGETS := $(BIN_DIR)/generate_sopmv $(BIN_DIR)/sopmv_sa $(BIN_DIR)/sopmv_greedy \
	$(BIN_DIR)/sopmv_ils $(BIN_DIR)/sopmv_ils_new_version $(BIN_DIR)/test_parser $(BIN_DIR)/test_small_instance \
	$(BIN_DIR)/test_greedy $(BIN_DIR)/test_ils $(BIN_DIR)/test_ils_acceptance
ifeq ($(strip $(CPLEX_ROOT_DIR)),)
ALL_TARGETS := $(CORE_TARGETS)
else
ALL_TARGETS := $(CORE_TARGETS) $(BIN_DIR)/sopmv_cplex \
		$(BIN_DIR)/sopmv_cplex_branch_cut $(BIN_DIR)/test_cplex_small \
		$(BIN_DIR)/test_cplex_berlin $(BIN_DIR)/test_cplex_branch_cut
endif

.PHONY: all test clean help check-cplex

all: $(ALL_TARGETS)

$(BIN_DIR):
	mkdir -p $@

$(BIN_DIR)/generate_sopmv: src/generate_main.cpp $(CORE_SOURCES) | $(BIN_DIR)
	$(CXX) $(STD) $(CXXFLAGS) $(WARNINGS) $(CPPFLAGS) $^ -o $@

$(BIN_DIR)/sopmv_sa: src/sa_pd/main.cpp src/sa_pd/sa_pd.cpp $(CORE_SOURCES) | $(BIN_DIR)
	$(CXX) $(STD) $(CXXFLAGS) $(WARNINGS) $(CPPFLAGS) $^ -o $@

$(BIN_DIR)/sopmv_greedy: src/greedy/main.cpp src/greedy/greedy.cpp $(CORE_SOURCES) | $(BIN_DIR)
	$(CXX) $(STD) $(CXXFLAGS) $(WARNINGS) $(CPPFLAGS) -Isrc/greedy $^ -o $@

$(BIN_DIR)/sopmv_ils: src/ils/main.cpp src/ils/ils.cpp src/greedy/greedy.cpp $(CORE_SOURCES) | $(BIN_DIR)
	$(CXX) $(STD) $(CXXFLAGS) $(WARNINGS) $(CPPFLAGS) -Isrc/ils -Isrc/greedy $^ -o $@

$(BIN_DIR)/sopmv_ils_new_version: src/ils/main.cpp src/ils/ils_new_version.cpp src/greedy/greedy.cpp $(CORE_SOURCES) | $(BIN_DIR)
	$(CXX) $(STD) $(CXXFLAGS) $(WARNINGS) $(CPPFLAGS) -Isrc/ils -Isrc/greedy $^ -o $@

$(BIN_DIR)/test_parser: tests/test_parser.cpp $(CORE_SOURCES) | $(BIN_DIR)
	$(CXX) $(STD) $(CXXFLAGS) $(WARNINGS) $(CPPFLAGS) $(TEST_DEFINE) $^ -o $@

$(BIN_DIR)/test_small_instance: tests/test_small_instance.cpp $(CORE_SOURCES) | $(BIN_DIR)
	$(CXX) $(STD) $(CXXFLAGS) $(WARNINGS) $(CPPFLAGS) $(TEST_DEFINE) $^ -o $@

$(BIN_DIR)/test_greedy: tests/test_greedy.cpp src/greedy/greedy.cpp $(CORE_SOURCES) | $(BIN_DIR)
	$(CXX) $(STD) $(CXXFLAGS) $(WARNINGS) $(CPPFLAGS) -Isrc/greedy $(TEST_DEFINE) $^ -o $@

$(BIN_DIR)/test_ils: tests/test_ils.cpp src/ils/ils.cpp src/greedy/greedy.cpp $(CORE_SOURCES) | $(BIN_DIR)
	$(CXX) $(STD) $(CXXFLAGS) $(WARNINGS) $(CPPFLAGS) -Isrc/ils -Isrc/greedy $(TEST_DEFINE) $^ -o $@

$(BIN_DIR)/test_ils_acceptance: tests/test_ils_acceptance.cpp src/ils/ils_new_version.cpp src/greedy/greedy.cpp $(CORE_SOURCES) | $(BIN_DIR)
	$(CXX) $(STD) $(CXXFLAGS) $(WARNINGS) $(CPPFLAGS) -Isrc/ils -Isrc/greedy $(TEST_DEFINE) $^ -o $@

check-cplex:
	@test -n "$(CPLEX_ROOT_DIR)" || \
		(printf '%s\n' 'Erro: defina CPLEX_ROOT_DIR para compilar o resolvedor.' >&2; exit 2)
	@test -f "$(CPLEX_INCLUDE)/ilcplex/ilocplex.h" || \
		(printf '%s\n' 'Erro: ilcplex/ilocplex.h nao encontrado em CPLEX_ROOT_DIR.' >&2; exit 2)

$(BIN_DIR)/sopmv_cplex: src/cplex/main.cpp src/cplex/sopmv_model.cpp $(CORE_SOURCES) | $(BIN_DIR) check-cplex
	$(CXX) $(STD) $(CXXFLAGS) $(WARNINGS) $(CPPFLAGS) $(CPLEX_CPPFLAGS) $^ $(CPLEX_LDLIBS) -o $@

$(BIN_DIR)/sopmv_cplex_branch_cut: src/cplex/main.cpp src/cplex/sopmv_model_branch_cut.cpp $(CORE_SOURCES) | $(BIN_DIR) check-cplex
	$(CXX) $(STD) $(CXXFLAGS) $(WARNINGS) $(CPPFLAGS) $(CPLEX_CPPFLAGS) -DSOPMV_BRANCH_AND_CUT $^ $(CPLEX_LDLIBS) -o $@

$(BIN_DIR)/test_cplex_small: tests/test_cplex_small.cpp src/cplex/sopmv_model.cpp $(CORE_SOURCES) | $(BIN_DIR) check-cplex
	$(CXX) $(STD) $(CXXFLAGS) $(WARNINGS) $(CPPFLAGS) $(CPLEX_CPPFLAGS) $(TEST_DEFINE) $^ $(CPLEX_LDLIBS) -o $@

$(BIN_DIR)/test_cplex_berlin: tests/test_cplex_berlin.cpp src/cplex/sopmv_model.cpp $(CORE_SOURCES) | $(BIN_DIR) check-cplex
	$(CXX) $(STD) $(CXXFLAGS) $(WARNINGS) $(CPPFLAGS) $(CPLEX_CPPFLAGS) $(TEST_DEFINE) $^ $(CPLEX_LDLIBS) -o $@

$(BIN_DIR)/test_cplex_branch_cut: tests/test_cplex_branch_cut.cpp src/cplex/sopmv_model_branch_cut.cpp $(CORE_SOURCES) | $(BIN_DIR) check-cplex
	$(CXX) $(STD) $(CXXFLAGS) $(WARNINGS) $(CPPFLAGS) $(CPLEX_CPPFLAGS) $(TEST_DEFINE) $^ $(CPLEX_LDLIBS) -o $@

test: all
	$(BIN_DIR)/test_parser
	$(BIN_DIR)/test_small_instance
	$(BIN_DIR)/test_greedy
	$(BIN_DIR)/test_ils
	$(BIN_DIR)/test_ils_acceptance
ifneq ($(strip $(CPLEX_ROOT_DIR)),)
	$(BIN_DIR)/test_cplex_small
	$(BIN_DIR)/test_cplex_berlin
	$(BIN_DIR)/test_cplex_branch_cut
else
	@printf '%s\n' 'Aviso: testes CPLEX ignorados; CPLEX_ROOT_DIR nao definido.'
endif

clean:
	rm -rf $(BUILD_DIR)

help:
	@printf '%s\n' \
		'make                         # parser, gerador e testes independentes' \
		'make CPLEX_ROOT_DIR=/opt/ibm/ILOG/CPLEX_Studio129' \
		'make test CPLEX_ROOT_DIR=/opt/ibm/ILOG/CPLEX_Studio129'
