from pydantic import BaseModel, Field

class AbdominalSchema(BaseModel):
    liver_size: str = Field(default="正常", description="肝脏大小")
    liver_echo: str = Field(default="均匀", description="肝脏实质回声")
    gallbladder_size: str = Field(default="正常", description="胆囊大小")
    gallbladder_wall: str = Field(default="光整", description="胆囊壁情况")
    other_findings: str = Field(default="", description="其他发现")

ABDOMINAL_FEW_SHOT = """
Example 1:
Input: 肝脏大个子，里边回声有点密密麻麻的密增强，胆囊小石头没看到，但是壁毛糙。
Output: {"liver_size": "增大", "liver_echo": "增强", "gallbladder_size": "正常", "gallbladder_wall": "毛糙", "other_findings": ""}
"""
