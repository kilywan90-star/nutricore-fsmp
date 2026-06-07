from pydantic import BaseModel, Field

class BreastSchema(BaseModel):
    left_breast_nodule: str = Field(default="未见明显结节", description="左乳结节情况")
    right_breast_nodule: str = Field(default="未见明显结节", description="右乳结节情况")
    bi_rads_grade: str = Field(default="1类", description="BI-RADS分级")
    other_findings: str = Field(default="", description="其他发现")

BREAST_FEW_SHOT = """
Example 1:
Input: 左乳房长了个包块，差不多两公分，边上看起来模模糊糊的，感觉是4a类。
Output: {"left_breast_nodule": "可见一大小约2cm结节，边界欠清", "right_breast_nodule": "未见明显结节", "bi_rads_grade": "4a类", "other_findings": ""}

Example 2:
Input: 右边乳腺没看到啥，左边也是好的，都没事。
Output: {"left_breast_nodule": "未见明显结节", "right_breast_nodule": "未见明显结节", "bi_rads_grade": "1类", "other_findings": ""}
"""
