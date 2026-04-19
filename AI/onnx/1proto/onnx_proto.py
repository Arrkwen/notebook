#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ONNX Proto 示例模块
===================
通过代码构造一个完整的 ONNX 模型，演示各 Proto 的作用与用法。

Proto 角色说明（对应 onnx.proto3 / onnx_cn.proto3）：
------------------------------------------------------
- ModelProto      : 顶层容器，包含 IR 版本、算子集引用、生产者信息、计算图、训练信息等
- GraphProto      : 计算图，由节点、输入输出、初始器、value_info、量化注解等组成
- NodeProto       : 图中一个算子节点，包含输入输出名、op_type、domain、属性等
- ValueInfoProto  : 描述某个值的名称、类型（含形状）、文档与元数据
- TensorProto     : 序列化张量（形状、数据类型、float_data/raw_data/external_data）
- AttributeProto  : 算子的命名属性，支持 float/int/string/tensor/graph 等单值或列表
- TypeProto       : 类型描述（张量/序列/映射/可选/稀疏张量），含 elem_type 与 shape
- OperatorSetIdProto : 算子集标识 (domain, version)，模型依赖的算子集
- TensorAnnotation   : 张量与其量化参数（scale、zero_point）的映射
- StringStringEntryProto : 键值对，用于 metadata_props、external_data 等
- TrainingInfoProto : 训练用初始化图与算法图、binding 等（本示例不展开）
- FunctionProto    : 模型内可复用的函数子图（本示例不展开）
"""

from __future__ import annotations

import numpy as np
from typing import List, Optional, Sequence, Tuple

# 使用 onnx 官方包构建模型（底层即 proto 结构）
import onnx
from onnx import (
    helper,
    TensorProto,
    ValueInfoProto,
    NodeProto,
    GraphProto,
    ModelProto,
    OperatorSetIdProto,
    TensorAnnotation,
    StringStringEntryProto,
)
from onnx import numpy_helper


# ---------------------------------------------------------------------------
# 常量：IR 版本与算子集（对应 Version 与 OperatorSetIdProto）
# ---------------------------------------------------------------------------
IR_VERSION = int(onnx.IR_VERSION)  # 当前 ONNX IR 版本
OPSET_DOMAIN = ""                   # 空表示 ONNX 标准算子集
OPSET_VERSION = 18                 # 使用的 opset 版本


def _make_tensor(
    name: str,
    data: np.ndarray,
    doc_string: str = "",
) -> TensorProto:
    """
    构造 TensorProto，演示：
    - name, dims, data_type
    - float_data / int64_data / raw_data 等存储方式之一
    - doc_string, external_data（本示例用默认存储）
    """
    return numpy_helper.from_array(data, name=name)


def _make_value_info(
    name: str,
    elem_type: int,
    shape: Sequence[int],
    doc_string: str = "",
) -> ValueInfoProto:
    """
    构造 ValueInfoProto，演示：
    - name：值（输入/输出/中间量）的名称
    - type：TypeProto，含 elem_type 与 TensorShapeProto（dim 列表）
    - doc_string、metadata_props（可选）
    """
    return helper.make_tensor_value_info(
        name, elem_type, list(shape),doc_string=doc_string
    )


def _make_node(
    op_type: str,
    inputs: List[str],
    outputs: List[str],
    name: Optional[str] = None,
    domain: str = "",
    **attrs,
) -> NodeProto:
    """
    构造 NodeProto，演示：
    - input / output：值名称列表
    - name：节点可选标识
    - op_type：算子类型；domain：算子集域
    - attribute：AttributeProto 列表（由 **attrs 转成）
    """
    node = helper.make_node(
        op_type, inputs, outputs,
        name=name, domain=domain or None, **attrs
    )
    return node


def _make_graph(
    name: str,
    inputs: List[ValueInfoProto],
    outputs: List[ValueInfoProto],
    initializer: List[TensorProto],
    nodes: List[NodeProto],
    value_info: Optional[List[ValueInfoProto]] = None,
    doc_string: str = "",
    quantization_annotation: Optional[List[TensorAnnotation]] = None,
    metadata_props: Optional[List[Tuple[str, str]]] = None,
) -> GraphProto:
    """
    构造 GraphProto，演示：
    - node：节点列表（拓扑序）
    - name：图名称
    - initializer：常量张量（可与 input 同名，表示可选输入）
    - input / output：图级输入输出
    - value_info：中间值的类型/形状信息（可选）
    - doc_string、quantization_annotation、metadata_props
    """
    value_info = value_info or []
    quantization_annotation = quantization_annotation or []
    metadata_props = metadata_props or []

    graph = helper.make_graph(
        nodes=nodes,
        name=name,
        inputs=inputs,
        outputs=outputs,
        initializer=initializer,
        value_info=value_info if value_info else None,
        doc_string=doc_string or None,
    )
    if quantization_annotation:
        graph.quantization_annotation.extend(quantization_annotation)
    for k, v in metadata_props:
        graph.metadata_props.append(StringStringEntryProto(key=k, value=v))
    return graph


def _make_model(
    graph: GraphProto,
    ir_version: int = IR_VERSION,
    producer_name: str = "onnx_proto_demo",
    producer_version: str = "1.0",
    domain: str = "",
    model_version: int = 1,
    doc_string: str = "",
    metadata_props: Optional[List[Tuple[str, str]]] = None,
) -> ModelProto:
    """
    构造 ModelProto，演示：
    - ir_version：IR 版本
    - opset_import：OperatorSetIdProto 列表
    - producer_name / producer_version / domain / model_version
    - graph：主计算图
    - doc_string、metadata_props
    """
    opset = OperatorSetIdProto(domain=OPSET_DOMAIN, version=OPSET_VERSION)
    kwargs = dict(
        ir_version=ir_version,
        producer_name=producer_name,
        producer_version=producer_version,
        model_version=model_version,
        opset_imports=[opset],
    )
    if domain:
        kwargs["domain"] = domain
    if doc_string:
        kwargs["doc_string"] = doc_string
    model = helper.make_model(graph, **kwargs)
    if metadata_props:
        for k, v in metadata_props:
            model.metadata_props.append(StringStringEntryProto(key=k, value=v))
    return model


# ---------------------------------------------------------------------------
# 示例：构造一个简单线性模型 y = X @ W + b
# 涉及：ModelProto, GraphProto, NodeProto, ValueInfoProto, TensorProto,
#      AttributeProto（通过 make_node 的 kwargs）, TypeProto（在 value_info 内）
# ---------------------------------------------------------------------------
def build_linear_demo_model(
    batch_size: int = 2,
    in_features: int = 4,
    out_features: int = 3,
) -> ModelProto:
    """
    构建一个最小可运行的 ONNX 模型：线性层 y = X @ W + b。
    用来说明各 proto 在真实模型中的角色。
    """
    # ------ 1. TensorProto：常量 W, b（作为 initializer）------
    W = _make_tensor(
        "W",
        np.random.randn(in_features, out_features).astype(np.float32),
    )
    b = _make_tensor("b", np.random.randn(out_features).astype(np.float32))

    # ------ 2. ValueInfoProto：图输入 X、图输出 Y、中间量（可选）------
    X_info = _make_value_info(
        "X", TensorProto.FLOAT, [batch_size, in_features],
        doc_string="输入张量 X",
    )
    Y_info = _make_value_info(
        "Y", TensorProto.FLOAT, [batch_size, out_features],
        doc_string="输出张量 Y",
    )
    matmul_out_info = _make_value_info(
        "matmul_out", TensorProto.FLOAT, [batch_size, out_features],
    )

    # ------ 3. NodeProto：MatMul -> Add ------
    node_matmul = _make_node(
        "MatMul", ["X", "W"], ["matmul_out"], name="Linear_MatMul",
    )
    node_add = _make_node(
        "Add", ["matmul_out", "b"], ["Y"], name="Linear_Add",
    )

    # ------ 4. GraphProto ------
    graph = _make_graph(
        name="linear_graph",
        inputs=[X_info],
        outputs=[Y_info],
        initializer=[W, b],
        nodes=[node_matmul, node_add],
        value_info=[matmul_out_info],
        doc_string="线性层示例图：Y = X @ W + b",
        metadata_props=[("graph_meta_key", "graph_meta_value")],
    )

    # ------ 5. ModelProto ------
    model = _make_model(
        graph,
        producer_name="onnx_proto_demo",
        producer_version="1.0",
        domain="",
        model_version=1,
        doc_string="演示各 Proto 用法的线性模型",
        metadata_props=[("model_meta_key", "model_meta_value")],
    )

    return model


def build_model_with_attributes_and_annotation() -> ModelProto:
    """
    在线性模型基础上，增加：
    - 更多 AttributeProto 的展示（通过带属性的算子）
    - TensorAnnotation（量化注解，仅做结构演示）
    实际量化需配套 scale/zero_point 等。
    """
    batch_size, in_f, out_f = 2, 4, 3
    W = _make_tensor("W", np.random.randn(in_f, out_f).astype(np.float32))
    b = _make_tensor("b", np.random.randn(out_f).astype(np.float32))

    X_info = _make_value_info("X", TensorProto.FLOAT, [batch_size, in_f])
    Y_info = _make_value_info("Y", TensorProto.FLOAT, [batch_size, out_f])

    # 使用带属性的算子：例如 Constant 的 value 是 AttributeProto(Tensor)
    # 这里用 MatMul + Add 保持简单，仅在图/模型上加注解
    nodes = [
        _make_node("MatMul", ["X", "W"], ["matmul_out"], name="MatMul_0"),
        _make_node("Add", ["matmul_out", "b"], ["Y"], name="Add_0"),
    ]

    # TensorAnnotation：描述张量 "W" 与量化参数名的映射（示例，不写真实 scale/zp）
    annot = TensorAnnotation(
        tensor_name="W",
        quant_parameter_tensor_names=[
            StringStringEntryProto(key="SCALE_TENSOR", value="W_scale"),
            StringStringEntryProto(key="ZERO_POINT_TENSOR", value="W_zero_point"),
        ],
    )

    graph = _make_graph(
        name="linear_with_annotation",
        inputs=[X_info],
        outputs=[Y_info],
        initializer=[W, b],
        nodes=nodes,
        doc_string="带 TensorAnnotation 的线性图",
        quantization_annotation=[annot],
    )

    return _make_model(graph, doc_string="演示 AttributeProto / TensorAnnotation 等")


# ---------------------------------------------------------------------------
# 校验与保存
# ---------------------------------------------------------------------------
def check_and_save(model: ModelProto, path: str = "linear_demo.onnx") -> None:
    """检查模型合法性并保存为 .onnx 文件。"""
    try:
        onnx.checker.check_model(model)
        print(f"[OK] 模型校验通过，已保存到: {path}")
    except Exception as e:
        print(f"[WARN] 校验未通过: {e}")
    onnx.save(model, path)


def print_proto_summary(model: ModelProto) -> None:
    """打印模型中各 proto 的简要信息，便于理解结构。"""
    print("========== ModelProto ==========")
    print(
        f"  ir_version={model.ir_version}, "
        f"producer={model.producer_name}/{model.producer_version}"
    )
    print(f"  opset_import: {[(o.domain or '(default)', o.version) for o in model.opset_import]}")
    print(f"  graph.name = {model.graph.name}")

    print("========== GraphProto ==========")
    g = model.graph
    print(f"  inputs: {[i.name for i in g.input]}")
    print(f"  outputs: {[o.name for o in g.output]}")
    print(f"  initializer: {[t.name for t in g.initializer]}")
    print(f"  nodes: {[n.op_type for n in g.node]}")

    print("========== NodeProto (示例) ==========")
    for n in g.node[:2]:
        print(
            f"  {n.name}: op_type={n.op_type}, "
            f"domain={n.domain or '(default)'}"
        )
        print(f"    input={list(n.input)}, output={list(n.output)}")
        if n.attribute:
            print(f"    attributes: {[a.name for a in n.attribute]}")

    if g.quantization_annotation:
        print("========== TensorAnnotation (示例) ==========")
        for a in g.quantization_annotation[:1]:
            qp = [(p.key, p.value) for p in a.quant_parameter_tensor_names]
            print(f"  tensor_name={a.tensor_name}, quant_parameter_tensor_names={qp}")


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------
def main() -> None:
    """构造示例模型、校验、保存并打印结构摘要。"""
    import os
    base = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(base, "linear_demo.onnx")
    out_path_anno = os.path.join(base, "linear_demo_with_annotation.onnx")

    print("构建线性模型 Y = X@W + b ...")
    model = build_linear_demo_model(batch_size=2, in_features=4, out_features=3)
    print_proto_summary(model)
    check_and_save(model, out_path)

    print("\n构建带 TensorAnnotation 的模型...")
    model_anno = build_model_with_attributes_and_annotation()
    check_and_save(model_anno, out_path_anno)
    print("完成。")


if __name__ == "__main__":
    main()
