from load_model import tokenizer, base_model, adapter_model


def chat(tokenizer, model, user_message, system_message="你是《黑神话：悟空》领域助手，回答准确、简明。"):
    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_message},
    ]

    text = tokenizer.apply_chat_template(
        messages,   # 会话历史
        chat_template=None,  # 聊天模板
        add_generation_prompt=True,  # 是否添加生成提示,让模型开始回答
        tokenize=False,  # 是否分词
        padding=False,  # 是否填充
        truncation=False,  # 是否截断
        max_length=None,  # 最大长度
        return_tensors=None,  # 返回张量
        return_dict=False,  # 是否返回字典
        tools=None,  # 工具
        documents=None,  # 文档
    )

    inputs = tokenizer([text], return_tensors="pt").to(model.device)
    outputs = model.generate(**inputs,
                             max_new_tokens=256,
                             do_sample=True,
                             top_p=0.95,
                             top_k=40,
                             repetition_penalty=1.1,
                             temperature=0.6,
                             pad_token_id=tokenizer.pad_token_id)

    # 跳过prompt
    generate_ids = [output_ids[len(input_ids):] for input_ids, output_ids in zip(
        inputs.input_ids, outputs)]
    response = tokenizer.batch_decode(
        generate_ids, skip_special_tokens=True)[0]
    return response


def test_base_model(user_message):
    response = chat(tokenizer, base_model, user_message)
    print("base_model: ", response)


def test_adapter_model(user_message):
    response = chat(tokenizer, adapter_model, user_message)
    print("adapter_model: ", response)


if __name__ == "__main__":
    user_message = "石敢当和石先锋有什么区别？"
    test_base_model(user_message)
    test_adapter_model(user_message)
