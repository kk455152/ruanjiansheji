#!/bin/bash

# 配置路径
BASE_DIR="./host"
FILES="$BASE_DIR/data*/data.csv"

# 清理功能
if [ "$1" == "clean" ]; then
    echo "🧹 正在重置 10 个节点的数据文件..."
    truncate -s 0 $FILES
    echo "✅ 清理完成！文件已归零。"
    exit 0
fi

echo "================================================================"
echo "          🌈 10-Node 彩色数据瀑布 (Full Spectrum)               "
echo "   提示: 按 Ctrl+C 停止 | 使用 './data_boss.sh clean' 清空       "
echo "================================================================"

# 使用 tail 实时追踪，并通过 awk 进行十色渲染
tail -f $FILES | awk '
    /^==>/ { 
        split($2, a, "/"); 
        node = a[3]; 
        next 
    } 
    NF { 
        if (node == "data1")  c = "31"; # 红
        else if (node == "data2")  c = "32"; # 绿
        else if (node == "data3")  c = "33"; # 黄
        else if (node == "data4")  c = "34"; # 蓝
        else if (node == "data5")  c = "35"; # 紫
        else if (node == "data6")  c = "36"; # 青
        else if (node == "data7")  c = "91"; # 亮红
        else if (node == "data8")  c = "92"; # 亮绿
        else if (node == "data9")  c = "93"; # 亮黄
        else if (node == "data10") c = "96"; # 亮青
        else c = "37"; # 其他白色
        
        printf "\033[%sm[%s]\033[0m %s\n", c, node, $0;
        fflush(); # 强制刷新输出，防止卡顿
    }
'
