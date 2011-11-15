#!/usr/bin/env python
#
# Copyright 2011 Ettus Research LLC
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

TMPL_HEADER = """
#import time
/***********************************************************************
 * This file was generated by $file on $time.strftime("%c")
 **********************************************************************/

\#include "convert_common.hpp"
\#include <uhd/utils/byteswap.hpp>

using namespace uhd::convert;
"""

TMPL_CONV_GEN2_ITEM32 = """
DECLARE_CONVERTER(item32, 1, sc16_item32_$(end), 1, PRIORITY_GENERAL){
    const item32_t *input = reinterpret_cast<const item32_t *>(inputs[0]);
    item32_t *output = reinterpret_cast<item32_t *>(outputs[0]);

    for (size_t i = 0; i < nsamps; i++){
        output[i] = $(to_wire)(input[i]);
    }
}

DECLARE_CONVERTER(sc16_item32_$(end), 1, item32, 1, PRIORITY_GENERAL){
    const item32_t *input = reinterpret_cast<const item32_t *>(inputs[0]);
    item32_t *output = reinterpret_cast<item32_t *>(outputs[0]);

    for (size_t i = 0; i < nsamps; i++){
        output[i] = $(to_host)(input[i]);
    }
}
"""

TMPL_CONV_GEN2_SC16 = """
DECLARE_CONVERTER($(cpu_type), 1, sc16_item32_$(end), 1, PRIORITY_GENERAL){
    const $(cpu_type)_t *input = reinterpret_cast<const $(cpu_type)_t *>(inputs[0]);
    item32_t *output = reinterpret_cast<item32_t *>(outputs[0]);

    for (size_t i = 0; i < nsamps; i++){
        output[i] = $(to_wire)($(cpu_type)_to_item32_sc16(input[i], scale_factor));
    }
}

DECLARE_CONVERTER(sc16_item32_$(end), 1, $(cpu_type), 1, PRIORITY_GENERAL){
    const item32_t *input = reinterpret_cast<const item32_t *>(inputs[0]);
    $(cpu_type)_t *output = reinterpret_cast<$(cpu_type)_t *>(outputs[0]);

    for (size_t i = 0; i < nsamps; i++){
        output[i] = item32_sc16_to_$(cpu_type)($(to_host)(input[i]), scale_factor);
    }
}
"""

TMPL_CONV_GEN2_SC8 = """
DECLARE_CONVERTER(sc8_item32_$(end), 1, $(cpu_type), 1, PRIORITY_GENERAL){
    const item32_t *input = reinterpret_cast<const item32_t *>(size_t(inputs[0]) & ~0x3);
    $(cpu_type)_t *output = reinterpret_cast<$(cpu_type)_t *>(outputs[0]);
    $(cpu_type)_t dummy;
    size_t num_samps = nsamps;

    if ((size_t(inputs[0]) & 0x3) != 0){
        const item32_t item0 = $(to_host)(*input++);
        item32_sc8_to_$(cpu_type)(item0, dummy, *output++, scale_factor);
        num_samps--;
    }

    const size_t num_pairs = num_samps/2;
    for (size_t i = 0, j = 0; i < num_pairs; i++, j+=2){
        const item32_t item_i = $(to_host)(input[i]);
        item32_sc8_to_$(cpu_type)(item_i, output[j], output[j+1], scale_factor);
    }

    if (num_samps != num_pairs*2){
        const item32_t item_n = $(to_host)(input[num_pairs]);
        item32_sc8_to_$(cpu_type)(item_n, output[num_samps-1], dummy, scale_factor);
    }
}
"""

TMPL_CONV_USRP1_COMPLEX = """
DECLARE_CONVERTER($(cpu_type), $(width), sc16_item16_usrp1, 1, PRIORITY_GENERAL){
    #for $w in range($width)
    const $(cpu_type)_t *input$(w) = reinterpret_cast<const $(cpu_type)_t *>(inputs[$(w)]);
    #end for
    boost::uint16_t *output = reinterpret_cast<boost::uint16_t *>(outputs[0]);

    for (size_t i = 0, j = 0; i < nsamps; i++){
        #for $w in range($width)
        output[j++] = $(to_wire)(boost::int16_t(input$(w)[i].real()$(do_scale)));
        output[j++] = $(to_wire)(boost::int16_t(input$(w)[i].imag()$(do_scale)));
        #end for
    }
}

DECLARE_CONVERTER(sc16_item16_usrp1, 1, $(cpu_type), $(width), PRIORITY_GENERAL){
    const boost::uint16_t *input = reinterpret_cast<const boost::uint16_t *>(inputs[0]);
    #for $w in range($width)
    $(cpu_type)_t *output$(w) = reinterpret_cast<$(cpu_type)_t *>(outputs[$(w)]);
    #end for

    for (size_t i = 0, j = 0; i < nsamps; i++){
        #for $w in range($width)
        output$(w)[i] = $(cpu_type)_t(
            boost::int16_t($(to_host)(input[j+0]))$(do_scale),
            boost::int16_t($(to_host)(input[j+1]))$(do_scale)
        );
        j += 2;
        #end for
    }
}

DECLARE_CONVERTER(sc8_item16_usrp1, 1, $(cpu_type), $(width), PRIORITY_GENERAL){
    const boost::uint16_t *input = reinterpret_cast<const boost::uint16_t *>(inputs[0]);
    #for $w in range($width)
    $(cpu_type)_t *output$(w) = reinterpret_cast<$(cpu_type)_t *>(outputs[$(w)]);
    #end for

    for (size_t i = 0, j = 0; i < nsamps; i++){
        #for $w in range($width)
        {
        const boost::uint16_t num = $(to_host)(input[j++]);
        output$(w)[i] = $(cpu_type)_t(
            boost::int8_t(num)$(do_scale),
            boost::int8_t(num >> 8)$(do_scale)
        );
        }
        #end for
    }
}
"""

def parse_tmpl(_tmpl_text, **kwargs):
    from Cheetah.Template import Template
    return str(Template(_tmpl_text, kwargs))

if __name__ == '__main__':
    import sys, os
    file = os.path.basename(__file__)
    output = parse_tmpl(TMPL_HEADER, file=file)

    #generate complex converters for all gen2 platforms
    for end, to_host, to_wire in (
        ('be', 'uhd::ntohx', 'uhd::htonx'),
        ('le', 'uhd::wtohx', 'uhd::htowx'),
    ):
        for cpu_type in 'fc64', 'fc32', 'sc16':
            output += parse_tmpl(
                TMPL_CONV_GEN2_SC16,
                end=end, to_host=to_host, to_wire=to_wire, cpu_type=cpu_type
            )
        for cpu_type in 'fc64', 'fc32', 'sc16', 'sc8':
            output += parse_tmpl(
                TMPL_CONV_GEN2_SC8,
                end=end, to_host=to_host, to_wire=to_wire, cpu_type=cpu_type
            )
        output += parse_tmpl(
                TMPL_CONV_GEN2_ITEM32,
                end=end, to_host=to_host, to_wire=to_wire
            )

    #generate complex converters for usrp1 format
    for width in 1, 2, 4:
        for cpu_type, do_scale in (
            ('fc64', '*scale_factor'),
            ('fc32', '*float(scale_factor)'),
            ('sc16', ''),
        ):
            output += parse_tmpl(
                TMPL_CONV_USRP1_COMPLEX,
                width=width, to_host='uhd::wtohx', to_wire='uhd::htowx',
                cpu_type=cpu_type, do_scale=do_scale
            )
    open(sys.argv[1], 'w').write(output)
