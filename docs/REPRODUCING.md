# 运行与结果再生成

## 1. 固定运行环境

沿用上一题的 SageMath 10.7 Docker 镜像。

```text
sagemath/sagemath@sha256:4f5589eb6c565949a006f8665de2876b8414410daf5ac554f4434a15d4f3d528
```

以下命令在项目根目录执行。安装了 SageMath 的环境可直接运行对应的 `sage -python` 命令。

## 2. 完整只读核验

Windows PowerShell 命令如下。

```powershell
docker run --rm --network none -e PYTHONDONTWRITEBYTECODE=1 -v "${PWD}:/workspace:ro" -w /workspace sagemath/sagemath@sha256:4f5589eb6c565949a006f8665de2876b8414410daf5ac554f4434a15d4f3d528 sage -python experiments/verify.py
```

macOS/Linux 命令如下。

```sh
docker run --rm --network none \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -v "$PWD:/workspace:ro" -w /workspace \
  sagemath/sagemath@sha256:4f5589eb6c565949a006f8665de2876b8414410daf5ac554f4434a15d4f3d528 \
  sage -python experiments/verify.py
```

预期退出码为零，报告包含以下字段。

```json
{
  "valid": true,
  "sage_version": "10.7",
  "symbolic_identity_count": 9,
  "primitive_check_count": 9,
  "cli_check_count": 3,
  "fixture_count": 40,
  "invalid_input_count": 9,
  "cubic_queries_per_construction": 1
}
```

## 3. 保存精确报告

将挂载改为可写，并增加 `--write`。

```powershell
docker run --rm --network none -e PYTHONDONTWRITEBYTECODE=1 -v "${PWD}:/workspace" -w /workspace sagemath/sagemath@sha256:4f5589eb6c565949a006f8665de2876b8414410daf5ac554f4434a15d4f3d528 sage -python experiments/verify.py --write
```

核验成功后更新 `experiments/results/verification.json` 和 `experiments/results/example.json`。默认输出和保存的报告内容相同。报告没有运行时间戳，以便固定环境中的重复运行进行逐字节比较。

## 4. 对自己的角执行构造

命令行接收有理数坐标。`--vertex` 默认为原点，`--first`、`--second` 为两条原射线上的非顶点标记。以下例子给出 $45^\circ$ 角，输出两条 $15^\circ$ 间隔的射线。

```powershell
docker run --rm --network none -e PYTHONDONTWRITEBYTECODE=1 -v "${PWD}:/workspace:ro" -w /workspace sagemath/sagemath@sha256:4f5589eb6c565949a006f8665de2876b8414410daf5ac554f4434a15d4f3d528 sage -python experiments/trisection.py --first 1 0 --second 1 1
```

顺时针及平移后的例子如下。坐标可以写成 `3/5` 等分数。

```powershell
docker run --rm --network none -e PYTHONDONTWRITEBYTECODE=1 -v "${PWD}:/workspace:ro" -w /workspace sagemath/sagemath@sha256:4f5589eb6c565949a006f8665de2876b8414410daf5ac554f4434a15d4f3d528 sage -python experiments/trisection.py --vertex 3 5 --first 5 5 --second 6 1
```

输出包含原角余弦、三分之一角余弦、两条射线的原顶点及射线上点、排列方向和给定曲线求交次数。每个代数数按精确证书格式返回。

非法输入以非零状态退出，并给出严格锐角要求。

分数可带负号。例如 `--vertex 1/3 -2/5 --first 4/3 -2/5 --second 4/3 3/5` 表示顶点位于 $(1/3,-2/5)$ 的 $45^\circ$ 角，负分数已包含在正式入口回归检查中。

## 5. Python 接口

在 SageMath Python 中，将 `experiments` 目录加入导入路径后，可以传入一般实代数坐标。

```python
import sys
sys.path.insert(0, "experiments")

from sage.all import AA
from trisection import construct_trisectors

result = construct_trisectors(
    (0, 0),
    (1, 0),
    (AA(1) / 2, AA(3).sqrt() / 2),
)
assert result.cubic_query_count == 1
first_ray, second_ray = result.rays
assert first_ray.vertex == (0, 0)
assert second_ray.vertex == (0, 0)
```

`result.construction` 保存全部命名对象与动作记录。其操作名称及几何含义见 [CONSTRUCTION](CONSTRUCTION.md)。该数据可以供第二阶段动画使用。

## 6. 再生成静态示意图

先按第 3 节生成最新报告，再执行绘图。SageMath 固定镜像已包含所用 Matplotlib 和 NumPy。

```powershell
docker run --rm --network none -e PYTHONDONTWRITEBYTECODE=1 -e MPLCONFIGDIR=/tmp/matplotlib -v "${PWD}:/workspace" -w /workspace sagemath/sagemath@sha256:4f5589eb6c565949a006f8665de2876b8414410daf5ac554f4434a15d4f3d528 sage -python experiments/plot_construction.py
```

该命令读取已核验的精确案例，并检查案例和源代码哈希，生成 `docs/figures/construction.png`。图中三个面板分别展示给定曲线与所作直线、正根到单位圆的提升，以及原位置的两条三等分射线。坐标均来自精确案例，浮点采样和角度函数用于显示曲线与角弧。
