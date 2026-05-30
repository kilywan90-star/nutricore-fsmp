"""HL7 v2 message parser.

Parses pipe-and-hat encoded HL7 v2 messages into structured dictionaries.

Supported message types:
  - ADT^A01: Inpatient admission
  - ADT^A08: Patient update
  - ORU^R01: Lab result
  - ORM^O01: Order entry (medication)

Segment encoding uses HL7 standard delimiters:
  - Field separator: |
  - Component separator: ^
  - Repetition separator: ~
  - Subcomponent separator: &
"""

from __future__ import annotations


class HL7Parser:
    """Parse HL7 v2.x pipe-and-hat encoded messages."""

    FIELD_SEP = "|"
    COMP_SEP = "^"
    REP_SEP = "~"
    SUBCOMP_SEP = "&"
    SEGMENT_SEP = "\r"  # segments are separated by \r (followed by optional \n)

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    @classmethod
    def _split_segments(cls, message: str) -> list[list[str]]:
        """Split a raw HL7 message into a list of segment field-lists."""
        # Normalize line endings: CR, LF, or CRLF all become standalone CR
        normalized = message.replace("\r\n", "\r").replace("\n", "\r")
        raw_segments = [s.strip() for s in normalized.split("\r") if s.strip()]
        return [seg.split(cls.FIELD_SEP) for seg in raw_segments]

    @classmethod
    def _get_segment(cls, segments: list[list[str]], name: str) -> list[str] | None:
        """Return the first occurrence of a named segment, or None."""
        for seg in segments:
            if seg and seg[0] == name:
                return seg
        return None

    @classmethod
    def _get_all_segments(cls, segments: list[list[str]], name: str) -> list[list[str]]:
        """Return all occurrences of a named segment."""
        return [seg for seg in segments if seg and seg[0] == name]

    @classmethod
    def _safe_field(cls, fields: list[str] | None, index: int, default: str = "") -> str:
        if fields and len(fields) > index:
            return fields[index]
        return default

    @classmethod
    def _safe_component(cls, composite: str, index: int, default: str = "") -> str:
        parts = composite.split(cls.COMP_SEP)
        if len(parts) > index:
            return parts[index]
        return default

    # ------------------------------------------------------------------
    # message type detection
    # ------------------------------------------------------------------

    @classmethod
    def detect_message_type(cls, message: str) -> str:
        """Detect the HL7 message type from MSH-9 (Message Type).

        Returns a string like "ADT^A01", "ORU^R01", "ORM^O01", or "UNKNOWN".
        """
        segments = cls._split_segments(message)
        msh = cls._get_segment(segments, "MSH")
        if msh is None:
            return "UNKNOWN"
        msg_type_field = cls._safe_field(msh, 8, "")
        if not msg_type_field:
            return "UNKNOWN"
        # MSH-9 is ^-separated: message_type^trigger_event
        parts = msg_type_field.split(cls.COMP_SEP)
        if len(parts) >= 2:
            return f"{parts[0]}^{parts[1]}"
        return msg_type_field

    # ------------------------------------------------------------------
    # ADT parsing (A01 admission, A08 update)
    # ------------------------------------------------------------------

    @classmethod
    def parse_adt(cls, message: str) -> dict:
        """Parse an ADT^A01 or ADT^A08 message.

        Returns a dict with patient_id, name (for hashing), gender, birth_date,
        admission_date, department, attending_doctor.
        """
        segments = cls._split_segments(message)
        pid = cls._get_segment(segments, "PID")
        pv1 = cls._get_segment(segments, "PV1")

        # --- PID segment ---
        # PID-3: Patient Identifier List (first repetition, first component = ID)
        pid_3 = cls._safe_field(pid, 3, "")
        patient_id = cls._safe_component(pid_3, 0)

        # PID-5: Patient Name (family^given^middle^suffix^prefix)
        pid_5 = cls._safe_field(pid, 5, "")
        family = cls._safe_component(pid_5, 0)
        given = cls._safe_component(pid_5, 1)
        name_for_hash = f"{family}{given}"

        # PID-8: Administrative Sex
        gender_code = cls._safe_field(pid, 8, "U")
        gender_map = {"M": "male", "F": "female", "U": "unknown", "O": "other"}
        gender = gender_map.get(gender_code.upper(), "unknown")

        # PID-7: Date of Birth (YYYYMMDD)
        birth_date = cls._safe_field(pid, 7, "")

        # --- PV1 segment ---
        # PV1-44: Admit Date/Time (YYYYMMDD[HHMMSS])
        admission_date = cls._safe_field(pv1, 44, "")

        # PV1-3: Assigned Patient Location (point_of_care^room^bed^facility^...)
        pv1_3 = cls._safe_field(pv1, 3, "")
        department = cls._safe_component(pv1_3, 3) or cls._safe_component(pv1_3, 0)

        # PV1-7: Attending Doctor (id^family^given^...)
        pv1_7 = cls._safe_field(pv1, 7, "")
        family_doc = cls._safe_component(pv1_7, 1)
        given_doc = cls._safe_component(pv1_7, 2)
        attending_doctor = f"{family_doc}{given_doc}".strip() or cls._safe_component(pv1_7, 0)

        # Parse birth_date from YYYYMMDD to YYYY format if available
        birth_year = 1970
        if len(birth_date) >= 4:
            try:
                birth_year = int(birth_date[:4])
            except (ValueError, TypeError):
                pass

        return {
            "patient_id": patient_id,
            "name": name_for_hash,
            "gender": gender,
            "birth_date": birth_date,
            "birth_year": birth_year,
            "admission_date": admission_date,
            "department": department,
            "attending_doctor": attending_doctor,
        }

    # ------------------------------------------------------------------
    # ORU^R01 parsing (lab result)
    # ------------------------------------------------------------------

    @classmethod
    def parse_oru(cls, message: str) -> dict:
        """Parse an ORU^R01 lab result message.

        Returns a dict with patient_id, order_number, and a list of observations,
        each containing test_code, test_name, result_value, unit, reference_range,
        abnormal_flag, result_date.
        """
        segments = cls._split_segments(message)
        pid = cls._get_segment(segments, "PID")
        obr = cls._get_segment(segments, "OBR")
        obx_list = cls._get_all_segments(segments, "OBX")

        # Patient ID from PID-3
        pid_3 = cls._safe_field(pid, 3, "")
        patient_id = cls._safe_component(pid_3, 0)

        # Order info from OBR
        order_number = ""
        if obr:
            # OBR-2: Placer Order Number, OBR-3: Filler Order Number
            order_number = cls._safe_field(obr, 3) or cls._safe_field(obr, 2)
            obr_7 = cls._safe_field(obr, 7, "")  # Observation Date/Time

        # Observations from OBX segments
        observations: list[dict] = []
        for obx in obx_list:
            # OBX-2: Value Type
            value_type = cls._safe_field(obx, 2, "NM")

            # OBX-3: Observation Identifier (identifier^text^coding_system)
            obx_3 = cls._safe_field(obx, 3, "")
            test_code = cls._safe_component(obx_3, 0)
            test_name = cls._safe_component(obx_3, 1)

            # OBX-5: Observation Value
            result_value_raw = cls._safe_field(obx, 5, "")
            result_value: str | float | None = result_value_raw
            if value_type == "NM" and result_value_raw:
                try:
                    result_value = float(result_value_raw)
                except (ValueError, TypeError):
                    result_value = result_value_raw

            # OBX-6: Units
            unit = cls._safe_field(obx, 6, "")

            # OBX-7: Reference Range
            reference_range = cls._safe_field(obx, 7, "")

            # OBX-8: Abnormal Flags (L=low, H=high, LL=critically low, HH=critically high)
            abnormal_flag = cls._safe_field(obx, 8, "")

            # OBX-14: Date/Time of Observation
            result_date = cls._safe_field(obx, 14, "") or cls._safe_field(obr, 7, "") if obr else ""

            observations.append({
                "test_code": test_code,
                "test_name": test_name,
                "result_value": result_value,
                "unit": unit,
                "reference_range": reference_range,
                "abnormal_flag": abnormal_flag,
                "result_date": result_date,
            })

        return {
            "patient_id": patient_id,
            "order_number": order_number,
            "observations": observations,
        }

    # ------------------------------------------------------------------
    # ORM^O01 parsing (order entry)
    # ------------------------------------------------------------------

    @classmethod
    def parse_orm(cls, message: str) -> dict:
        """Parse an ORM^O01 medication order message.

        Returns a dict with patient_id and a list of medication orders, each
        containing order_number, drug_code, drug_name, dose, route, frequency,
        start_date, ordering_doctor.
        """
        segments = cls._split_segments(message)
        pid = cls._get_segment(segments, "PID")
        orc_list = cls._get_all_segments(segments, "ORC")
        rxo_list = cls._get_all_segments(segments, "RXO")

        # Patient ID
        pid_3 = cls._safe_field(pid, 3, "")
        patient_id = cls._safe_component(pid_3, 0)

        # Build a map of ORC-2 (placer order number) -> ORC-12 (ordering provider)
        orc_providers: dict[str, str] = {}
        orc_numbers: list[str] = []
        for orc in orc_list:
            orc_2 = cls._safe_field(orc, 2, "")
            if orc_2:
                orc_numbers.append(orc_2)
                # ORC-12: Ordering Provider (id^family^given^...)
                orc_12 = cls._safe_field(orc, 12, "")
                family_doc = cls._safe_component(orc_12, 1)
                given_doc = cls._safe_component(orc_12, 2)
                provider = f"{family_doc}{given_doc}".strip() or cls._safe_component(orc_12, 0)
                orc_providers[orc_2] = provider

        # Parse RXO segments
        medication_orders: list[dict] = []
        for i, rxo in enumerate(rxo_list):
            # RXO-1: Requested Give Code (code^name^coding_system)
            rxo_1 = cls._safe_field(rxo, 1, "")
            drug_code = cls._safe_component(rxo_1, 0)
            drug_name = cls._safe_component(rxo_1, 1)

            # RXO-2: Requested Give Amount - Minimum
            dose = cls._safe_field(rxo, 2, "")

            # RXO-3: Requested Give Amount - Maximum (optional)
            dose_max = cls._safe_field(rxo, 3, "")
            if dose_max:
                dose = f"{dose}-{dose_max}"

            # RXO-4: Requested Give Units
            dose_units = cls._safe_field(rxo, 4, "")
            if dose_units:
                dose = f"{dose} {dose_units}".strip()

            # RXO-5: Requested Dosage Form (not typically in RXO, but used in some impl)
            # RxO-8: Administration Route — typically from RXE in a full message,
            #        but some systems encode it in RXO-8 or in an RXE segment.
            route = cls._safe_field(rxo, 8, "")

            # RXO-6: Provider's Administration Instructions
            admin_instructions = cls._safe_field(rxo, 6, "")

            # Frequency / timing from ORC or RXO
            frequency = admin_instructions

            # ORC-7: Quantity/Timing or ORC-9: Date/Time of Transaction
            # Approximate start_date from matching ORC
            order_number = orc_numbers[i] if i < len(orc_numbers) else ""
            start_date = ""
            if order_number:
                # Try to get ORC-7 (quantity/timing) or ORC-9 (date/time)
                pass

            ordering_doctor = orc_providers.get(order_number, "")

            # RXO-15 (some systems): Order Effective Date/Time
            start_date = cls._safe_field(rxo, 15, "") or start_date

            medication_orders.append({
                "order_number": order_number,
                "drug_code": drug_code,
                "drug_name": drug_name,
                "dose": dose,
                "route": route,
                "frequency": frequency,
                "start_date": start_date,
                "ordering_doctor": ordering_doctor,
            })

        return {
            "patient_id": patient_id,
            "medication_orders": medication_orders,
        }
