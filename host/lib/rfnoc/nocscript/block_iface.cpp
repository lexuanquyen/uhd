//
// Copyright 2015 Ettus Research LLC
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <http://www.gnu.org/licenses/>.
//

#include "block_iface.hpp"
#include "function_table.hpp"
#include <uhd/exception.hpp>
#include <uhd/utils/msg.hpp>
#include <boost/assign.hpp>
#include <boost/bind.hpp>
#include <boost/format.hpp>

using namespace uhd::rfnoc;
using namespace uhd::rfnoc::nocscript;

block_iface::block_iface(block_ctrl_base *block_ptr)
    : _block_ptr(block_ptr)
{
    function_table::sptr ft = function_table::make();

    // Add the SR_WRITE() function
    expression_function::argtype_list_type sr_write_args = boost::assign::list_of
        (expression::TYPE_STRING)
        (expression::TYPE_INT)
    ;
    ft->register_function(
        "SR_WRITE",
        boost::bind(&block_iface::_nocscript__sr_write, this, _1),
        expression::TYPE_BOOL,
        sr_write_args
    );

    // Add read access to arguments ($foo)
    expression_function::argtype_list_type arg_set_args_wo_port = boost::assign::list_of
        (expression::TYPE_STRING)
        (expression::TYPE_INT)
    ;
    expression_function::argtype_list_type arg_set_args_w_port = boost::assign::list_of
        (expression::TYPE_STRING)
        (expression::TYPE_INT)
        (expression::TYPE_INT)
    ;
#define REGISTER_ARG_SETTER(noctype, setter_func) \
    arg_set_args_wo_port[1] = expression::noctype; \
    arg_set_args_w_port[1] = expression::noctype; \
    ft->register_function( \
        "SET_ARG", \
        boost::bind(&block_iface::setter_func, this, _1), \
        expression::TYPE_BOOL, \
        arg_set_args_wo_port \
    ); \
    ft->register_function( \
        "SET_ARG", \
        boost::bind(&block_iface::setter_func, this, _1), \
        expression::TYPE_BOOL, \
        arg_set_args_w_port \
    );
    REGISTER_ARG_SETTER(TYPE_INT,        _nocscript__arg_set_int);
    REGISTER_ARG_SETTER(TYPE_STRING,     _nocscript__arg_set_string);
    REGISTER_ARG_SETTER(TYPE_DOUBLE,     _nocscript__arg_set_double);
    REGISTER_ARG_SETTER(TYPE_INT_VECTOR, _nocscript__arg_set_intvec);
    );

    // Create the parser
    _parser = parser::make(
        ft,
        boost::bind(&block_iface::_nocscript__arg_get_type, this, _1),
        boost::bind(&block_iface::_nocscript__arg_get_val,  this, _1)
    );
}


void block_iface::run_and_check(const std::string &code, const std::string &error_message)
{
    boost::mutex::scoped_lock local_interpreter_lock(_lil_mutex);

    UHD_MSG(status) << "[NocScript] Executing and asserting code: " << code << std::endl;
    expression::sptr e = _parser->create_expr_tree(code);
    expression_literal result = e->eval();
    if (not result.to_bool()) {
        if (error_message.empty()) {
            throw uhd::runtime_error(str(
                boost::format("[NocScript] Code returned false: %s")
                % code
            ));
        } else {
            throw uhd::runtime_error(str(
                boost::format("[NocScript] Error: %s")
                % error_message
            ));
        }
    }
}


expression_literal block_iface::_nocscript__sr_write(expression_container::expr_list_type args)
{
    const std::string reg_name = args[0]->eval().get_string();
    const boost::uint32_t reg_val = boost::uint32_t(args[1]->eval().get_int());
    bool result = true;
    try {
        UHD_MSG(status) << "[NocScript] Executing SR_WRITE() " << std::endl;
        _block_ptr->sr_write(reg_name, reg_val);
    } catch (const uhd::exception &e) {
        UHD_MSG(error) << boost::format("[NocScript] Error while executing SR_WRITE(%s, 0x%X):\n%s")
                          % reg_name % reg_val % e.what()
                       << std::endl;
        result = false;
    }

    return expression_literal(result);
}

expression::type_t block_iface::_nocscript__arg_get_type(const std::string &varname)
{
    const std::string var_type = _block_ptr->get_arg_type(varname);
    if (var_type == "int") {
        return expression::TYPE_INT;
    } else if (var_type == "string") {
        return expression::TYPE_STRING;
    } else if (var_type == "double") {
        return expression::TYPE_DOUBLE;
    } else if (var_type == "int_vector") {
        UHD_THROW_INVALID_CODE_PATH(); // TODO
    } else {
        UHD_THROW_INVALID_CODE_PATH();
    }
}

expression_literal block_iface::_nocscript__arg_get_val(const std::string &varname)
{
    const std::string var_type = _block_ptr->get_arg_type(varname);
    if (var_type == "int") {
        return expression_literal(_block_ptr->get_arg<int>(varname));
    } else if (var_type == "string") {
        return expression_literal(_block_ptr->get_arg<std::string>(varname));
    } else if (var_type == "double") {
        return expression_literal(_block_ptr->get_arg<double>(varname));
    } else if (var_type == "int_vector") {
        UHD_THROW_INVALID_CODE_PATH(); // TODO
    } else {
        UHD_THROW_INVALID_CODE_PATH();
    }
}

expression_literal block_iface::_nocscript__arg_set_int(const expression_container::expr_list_type &args)
{
    const std::string var_name = args[0]->eval().get_string();
    const int val              = args[1]->eval().get_int();
    size_t port = 0;
    if (args.size() == 3) {
        port = size_t(args[2]->eval().get_int());
    }
    UHD_MSG(status) << "[NocScript] Setting $" << var_name << std::endl;
    _block_ptr->set_arg<int>(var_name, val, port);
    return expression_literal(true);
}

expression_literal block_iface::_nocscript__arg_set_string(const expression_container::expr_list_type &args)
{
    const std::string var_name = args[0]->eval().get_string();
    const std::string val      = args[1]->eval().get_string();
    size_t port = 0;
    if (args.size() == 3) {
        port = size_t(args[2]->eval().get_int());
    }
    UHD_MSG(status) << "[NocScript] Setting $" << var_name << std::endl;
    _block_ptr->set_arg<std::string>(var_name, val, port);
    return expression_literal(true);
}

expression_literal block_iface::_nocscript__arg_set_double(const expression_container::expr_list_type &args)
{
    const std::string var_name = args[0]->eval().get_string();
    const double val              = args[1]->eval().get_double();
    size_t port = 0;
    if (args.size() == 3) {
        port = size_t(args[2]->eval().get_int());
    }
    UHD_MSG(status) << "[NocScript] Setting $" << var_name << std::endl;
    _block_ptr->set_arg<double>(var_name, val, port);
    return expression_literal(true);
}

expression_literal block_iface::_nocscript__arg_set_intvec(const expression_container::expr_list_type &)
{
    UHD_THROW_INVALID_CODE_PATH();
}

block_iface::sptr block_iface::make(uhd::rfnoc::block_ctrl_base* block_ptr)
{
    return sptr(new block_iface(block_ptr));
}

